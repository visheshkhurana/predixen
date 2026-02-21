"""
Prompt Injection Defense Module for FounderConsole Copilot.

This module provides utilities to sanitize user input and safely include
it in LLM prompts by:
1. Stripping/escaping potential prompt injection patterns
2. Using XML delimiters to clearly separate system instructions from user content
3. Validating and constraining input before inclusion in prompts

Security Principle: User content should NEVER be directly interpolated into
system prompts. Always use explicit delimiters and sanitization.
"""

import re
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class PromptInjectionDefense:
    """Utilities for defending against prompt injection attacks."""

    # Patterns that indicate potential prompt injection attempts
    INJECTION_PATTERNS = [
        r"(?i)(ignore|disregard|forget).*instructions",
        r"(?i)system\s*prompt",
        r"(?i)forget.*your.*role",
        r"(?i)you.*are.*now",
        r"(?i)pretend.*you.*are",
        r"(?i)from.*now.*on",
        r"(?i)(role\s*play|roleplay)",
        r"(?i)new\s*(instructions|guidelines|rules)",
        r"(?i)override",
        r"(?i)execute|run|eval",
    ]

    @staticmethod
    def sanitize_user_input(
        user_input: str,
        max_length: int = 10000,
        allow_newlines: bool = True
    ) -> str:
        """
        Sanitize user input to remove potential prompt injection attempts.

        Args:
            user_input: The raw user input string
            max_length: Maximum allowed length (to prevent token flooding)
            allow_newlines: Whether to allow newline characters

        Returns:
            Sanitized input string
        """
        if not isinstance(user_input, str):
            user_input = str(user_input)

        # Truncate to max length
        if len(user_input) > max_length:
            logger.warning(
                f"User input truncated from {len(user_input)} to {max_length} characters"
            )
            user_input = user_input[:max_length]

        # Remove control characters (except newlines if allowed)
        if allow_newlines:
            # Keep newlines and tabs, remove other control chars
            user_input = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', user_input)
        else:
            # Remove all control characters
            user_input = re.sub(r'[\x00-\x1f\x7f]', '', user_input)

        # Log potential injection attempts
        for pattern in PromptInjectionDefense.INJECTION_PATTERNS:
            if re.search(pattern, user_input):
                logger.warning(
                    f"Potential prompt injection detected in user input: "
                    f"matched pattern {pattern}"
                )

        return user_input.strip()

    @staticmethod
    def wrap_user_message(content: str) -> str:
        """
        Wrap user message in XML delimiters to clearly separate it from system instructions.

        This makes it explicit to the LLM that this content is from the user
        and should not be treated as system instructions.

        Args:
            content: The user message content

        Returns:
            User message wrapped in XML delimiters
        """
        # First sanitize the content
        content = PromptInjectionDefense.sanitize_user_input(content)

        # Escape any XML special characters in the content
        content = content.replace('&', '&amp;')
        content = content.replace('<', '&lt;')
        content = content.replace('>', '&gt;')
        content = content.replace('"', '&quot;')
        content = content.replace("'", '&apos;')

        return f"<user_message>\n{content}\n</user_message>"

    @staticmethod
    def wrap_user_data(label: str, content: Any) -> str:
        """
        Wrap structured user data in XML delimiters.

        Useful for company names, scenario names, and other structured data
        that may be user-controlled.

        Args:
            label: Label for the data (e.g., "company_name", "scenario_name")
            content: The data content (will be converted to string)

        Returns:
            Data wrapped in labeled XML delimiters
        """
        content_str = str(content) if content is not None else ""

        # Sanitize the content
        content_str = PromptInjectionDefense.sanitize_user_input(
            content_str,
            allow_newlines=False  # No newlines in structured data
        )

        # Escape XML special characters
        content_str = content_str.replace('&', '&amp;')
        content_str = content_str.replace('<', '&lt;')
        content_str = content_str.replace('>', '&gt;')
        content_str = content_str.replace('"', '&quot;')
        content_str = content_str.replace("'", '&apos;')

        # Use a tag-like format for labeled data
        return f"<{label}>{content_str}</{label}>"

    @staticmethod
    def create_safe_prompt_context(
        base_system_prompt: str,
        user_query: str,
        context_data: Optional[Dict[str, Any]] = None
    ) -> tuple[str, List[Dict[str, str]]]:
        """
        Create a safe prompt with proper separation between system instructions
        and user content.

        This is the preferred way to construct prompts with user input.

        Args:
            base_system_prompt: The system prompt (untouched, no user input)
            user_query: The user's query (will be sanitized and wrapped)
            context_data: Optional dict of context data to include
                         Keys will be used as labels, values as content

        Returns:
            Tuple of (system_prompt, messages)
            - system_prompt: The full system prompt with context
            - messages: List of message dicts for the LLM API
        """
        sanitized_query = PromptInjectionDefense.sanitize_user_input(user_query)
        wrapped_message = PromptInjectionDefense.wrap_user_message(sanitized_query)

        # Build context block if provided
        context_block = ""
        if context_data:
            context_block = "\n\n<context>\n"
            for key, value in context_data.items():
                if value is not None:
                    # Sanitize data
                    value_str = str(value)
                    value_str = PromptInjectionDefense.sanitize_user_input(
                        value_str,
                        allow_newlines=True
                    )
                    # Escape XML chars
                    value_str = value_str.replace('&', '&amp;')
                    value_str = value_str.replace('<', '&lt;')
                    value_str = value_str.replace('>', '&gt;')
                    value_str = value_str.replace('"', '&quot;')
                    value_str = value_str.replace("'", '&apos;')

                    context_block += f"  <{key}>{value_str}</{key}>\n"
            context_block += "</context>"

        full_system = base_system_prompt + context_block

        messages = [
            {"role": "user", "content": wrapped_message}
        ]

        return full_system, messages

    @staticmethod
    def validate_user_query(query: str, min_length: int = 1, max_length: int = 10000) -> tuple[bool, Optional[str]]:
        """
        Validate user query for safety and reasonableness.

        Args:
            query: The user query to validate
            min_length: Minimum query length
            max_length: Maximum query length

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if query passes validation
            - error_message: Error message if validation failed, None otherwise
        """
        if not isinstance(query, str):
            return False, "Query must be a string"

        if len(query) < min_length:
            return False, f"Query too short (minimum {min_length} characters)"

        if len(query) > max_length:
            return False, f"Query too long (maximum {max_length} characters)"

        # Check if query is just whitespace
        if not query.strip():
            return False, "Query cannot be empty or whitespace only"

        return True, None


def sanitize_prompt_template(template: str, **kwargs) -> str:
    """
    Safely format a prompt template with user-provided values.

    This function sanitizes all values before inserting them into the template.
    The template should use {key} placeholders.

    Args:
        template: The prompt template string
        **kwargs: Values to insert (will be sanitized)

    Returns:
        Formatted prompt with sanitized values

    Example:
        template = "For company {company_name}, analyze..."
        result = sanitize_prompt_template(template, company_name="Acme Inc")
    """
    # Sanitize all kwargs values
    sanitized = {}
    for key, value in kwargs.items():
        if isinstance(value, str):
            sanitized[key] = PromptInjectionDefense.sanitize_user_input(value)
        else:
            sanitized[key] = value

    # Format the template
    return template.format(**sanitized)


def build_agent_system_prompt(
    base_prompt: str,
    company_name: Optional[str] = None,
    industry: Optional[str] = None,
    stage: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Build an agent system prompt with safely integrated company context.

    All user-controlled data (company name, industry, stage) is sanitized
    and wrapped in XML delimiters before inclusion.

    Args:
        base_prompt: The base system prompt
        company_name: Company name (user-controlled)
        industry: Industry (user-controlled)
        stage: Company stage (user-controlled)
        additional_context: Additional context dict (all values are sanitized)

    Returns:
        Complete system prompt with safely integrated context
    """
    # Build context block with sanitized values
    context_lines = []

    if company_name:
        sanitized_name = PromptInjectionDefense.sanitize_user_input(
            company_name,
            allow_newlines=False
        )
        context_lines.append(f"<company_name>{sanitized_name}</company_name>")

    if industry:
        sanitized_industry = PromptInjectionDefense.sanitize_user_input(
            industry,
            allow_newlines=False
        )
        context_lines.append(f"<industry>{sanitized_industry}</industry>")

    if stage:
        sanitized_stage = PromptInjectionDefense.sanitize_user_input(
            stage,
            allow_newlines=False
        )
        context_lines.append(f"<stage>{sanitized_stage}</stage>")

    if additional_context:
        for key, value in additional_context.items():
            if value is not None:
                value_str = str(value)
                value_str = PromptInjectionDefense.sanitize_user_input(value_str)
                value_str = value_str.replace('&', '&amp;')
                value_str = value_str.replace('<', '&lt;')
                value_str = value_str.replace('>', '&gt;')
                context_lines.append(f"<{key}>{value_str}</{key}>")

    context_section = ""
    if context_lines:
        context_section = "\n\n<!-- Company Context (user-controlled data) -->\n"
        context_section += "<company_context>\n"
        context_section += "\n".join(context_lines)
        context_section += "\n</company_context>\n"

    return base_prompt + context_section
