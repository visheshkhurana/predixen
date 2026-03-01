import { useState } from "react";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useToast } from "@/hooks/use-toast";
import { Mail, Clock, Globe, Twitter, Linkedin, Github } from "lucide-react";
import { Loader2 } from "lucide-react";

const contactSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().email("Please enter a valid email address"),
  subject: z.string().min(1, "Please select a subject"),
  message: z.string().min(10, "Message must be at least 10 characters"),
});

type ContactFormValues = z.infer<typeof contactSchema>;

const faqs = [
  {
    question: "How quickly will I receive a response?",
    answer:
      "We aim to respond to all inquiries within 24 hours during business days. For urgent support issues, premium plan customers receive priority responses within 4 hours.",
  },
  {
    question: "Do you offer product demos?",
    answer:
      "Yes, we offer personalized demos for teams and enterprise customers. Select 'Sales' as your subject and mention you'd like a demo. We'll schedule a 30-minute walkthrough tailored to your startup's stage and needs.",
  },
  {
    question: "Can I request a new integration or feature?",
    answer:
      "Absolutely. We love hearing what founders need. Submit your request through this form with 'General Inquiry' as the subject, and our product team will review it. Many of our most popular features started as founder requests.",
  },
  {
    question: "Is there a community or Slack group I can join?",
    answer:
      "We're building a founder community around financial intelligence. Reach out via the contact form to get early access to our community channels where you can connect with other data-driven founders.",
  },
  {
    question: "What if I need help migrating from spreadsheets?",
    answer:
      "We offer white-glove onboarding for teams moving from spreadsheets. Our data team will help you map your existing models into FounderConsole and validate the migration with side-by-side comparisons.",
  },
];

const contactInfo = [
  {
    icon: Mail,
    title: "Email",
    detail: "hello@founderconsole.ai",
  },
  {
    icon: Clock,
    title: "Response Time",
    detail: "Within 24 hours",
  },
  {
    icon: Globe,
    title: "Office Hours",
    detail: "Mon–Fri, 9 AM – 6 PM IST",
  },
];

export default function ContactPage() {
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const form = useForm<ContactFormValues>({
    resolver: zodResolver(contactSchema),
    defaultValues: {
      name: "",
      email: "",
      subject: "",
      message: "",
    },
  });

  async function onSubmit(data: ContactFormValues) {
    setIsSubmitting(true);
    await new Promise((resolve) => setTimeout(resolve, 1200));
    setIsSubmitting(false);
    toast({
      title: "Message sent",
      description: `Thanks ${data.name}, we'll get back to you at ${data.email} shortly.`,
    });
    form.reset();
  }

  return (
    <MarketingLayout>
      <section className="py-20 sm:py-28" data-testid="section-contact-hero">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <h1
            className="text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl"
            data-testid="text-contact-headline"
          >
            Get in Touch
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground" data-testid="text-contact-subheadline">
            Have a question, partnership idea, or need support? We'd love to hear from you.
          </p>
        </div>
      </section>

      <section className="pb-20" data-testid="section-contact-form">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 gap-10 lg:grid-cols-2">
            <Card data-testid="card-contact-form">
              <CardContent className="pt-6">
                <Form {...form}>
                  <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
                    <FormField
                      control={form.control}
                      name="name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Name</FormLabel>
                          <FormControl>
                            <Input placeholder="Your name" data-testid="input-name" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="email"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Email</FormLabel>
                          <FormControl>
                            <Input
                              type="email"
                              placeholder="you@company.com"
                              data-testid="input-email"
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="subject"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Subject</FormLabel>
                          <Select onValueChange={field.onChange} value={field.value}>
                            <FormControl>
                              <SelectTrigger data-testid="select-subject">
                                <SelectValue placeholder="Select a subject" />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              <SelectItem value="general" data-testid="option-general">
                                General Inquiry
                              </SelectItem>
                              <SelectItem value="sales" data-testid="option-sales">
                                Sales
                              </SelectItem>
                              <SelectItem value="support" data-testid="option-support">
                                Support
                              </SelectItem>
                              <SelectItem value="partnership" data-testid="option-partnership">
                                Partnership
                              </SelectItem>
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="message"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Message</FormLabel>
                          <FormControl>
                            <Textarea
                              placeholder="Tell us how we can help..."
                              className="resize-none"
                              rows={5}
                              data-testid="input-message"
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <Button type="submit" disabled={isSubmitting} data-testid="button-submit-contact">
                      {isSubmitting ? (
                        <>
                          <Loader2 className="animate-spin" />
                          Sending...
                        </>
                      ) : (
                        "Send Message"
                      )}
                    </Button>
                  </form>
                </Form>
              </CardContent>
            </Card>

            <div className="space-y-6">
              {contactInfo.map((info) => (
                <Card key={info.title} data-testid={`card-info-${info.title.toLowerCase().replace(/\s+/g, "-")}`}>
                  <CardContent className="flex items-center gap-4 pt-6">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-primary/10">
                      <info.icon className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold">{info.title}</h3>
                      <p className="text-sm text-muted-foreground">{info.detail}</p>
                    </div>
                  </CardContent>
                </Card>
              ))}

              <Card data-testid="card-social-links">
                <CardContent className="pt-6">
                  <Label className="text-sm font-semibold mb-3 block">Follow Us</Label>
                  <div className="flex items-center gap-4 flex-wrap">
                    <a
                      href="https://twitter.com"
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label="Twitter"
                      data-testid="link-contact-twitter"
                      className="text-muted-foreground transition-colors"
                    >
                      <Twitter className="h-5 w-5" />
                    </a>
                    <a
                      href="https://linkedin.com"
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label="LinkedIn"
                      data-testid="link-contact-linkedin"
                      className="text-muted-foreground transition-colors"
                    >
                      <Linkedin className="h-5 w-5" />
                    </a>
                    <a
                      href="https://github.com"
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label="GitHub"
                      data-testid="link-contact-github"
                      className="text-muted-foreground transition-colors"
                    >
                      <Github className="h-5 w-5" />
                    </a>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      <section className="pb-20" data-testid="section-contact-faq">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-semibold mb-6 text-center" data-testid="text-faq-mini-title">
            Common Questions
          </h2>
          <Accordion type="single" collapsible className="w-full">
            {faqs.map((faq, i) => (
              <AccordionItem key={i} value={`faq-${i}`} data-testid={`accordion-faq-${i}`}>
                <AccordionTrigger data-testid={`button-faq-${i}`}>{faq.question}</AccordionTrigger>
                <AccordionContent data-testid={`text-faq-answer-${i}`}>
                  <p className="text-muted-foreground">{faq.answer}</p>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </section>
    </MarketingLayout>
  );
}
