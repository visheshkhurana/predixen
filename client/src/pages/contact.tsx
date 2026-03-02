import { useState } from "react";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { useSEO } from "@/lib/seo";
import { useToast } from "@/hooks/use-toast";
import { Mail, Clock, MessageSquare, Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

const contactSchema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().email("Valid email required"),
  subject: z.string().min(1, "Subject is required"),
  message: z.string().min(10, "Message must be at least 10 characters"),
});

type ContactForm = z.infer<typeof contactSchema>;

const contactFaq = [
  {
    question: "How quickly do you respond?",
    answer: "We aim to respond to all inquiries within 24 hours during business days.",
  },
  {
    question: "Can I schedule a demo?",
    answer: "Yes — mention 'demo request' in your message and we'll set up a personalized walkthrough.",
  },
  {
    question: "Do you offer enterprise support?",
    answer: "Yes. Contact us with details about your team size and requirements for custom pricing.",
  },
  {
    question: "How do I report a bug?",
    answer: "Select 'Support' as your subject and describe the issue. Include screenshots if possible.",
  },
];

export default function ContactPage() {
  useSEO({
    title: "Contact | FounderConsole",
    description: "Get in touch with the FounderConsole team. We respond within 24 hours.",
  });

  const { toast } = useToast();
  const [submitting, setSubmitting] = useState(false);

  const { register, handleSubmit, reset, formState: { errors }, setValue, watch } = useForm<ContactForm>({
    resolver: zodResolver(contactSchema),
    defaultValues: { name: "", email: "", subject: "", message: "" },
  });

  const onSubmit = async (data: ContactForm) => {
    setSubmitting(true);
    await new Promise((r) => setTimeout(r, 1000));
    setSubmitting(false);
    toast({ title: "Message sent", description: "We'll get back to you within 24 hours." });
    reset();
  };

  return (
    <MarketingLayout>
      <section>
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl" data-testid="text-contact-title">
            Get in Touch
          </h1>
          <p className="mt-3 max-w-2xl text-lg text-muted-foreground">
            Questions, feedback, or partnership inquiries — we'd love to hear from you.
          </p>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-10">
          <div className="grid gap-10 md:grid-cols-2">
            <div>
              <h2 className="text-lg font-semibold text-foreground">Send us a message</h2>
              <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4" data-testid="form-contact">
                <div className="space-y-2">
                  <Label htmlFor="name">Name</Label>
                  <Input id="name" placeholder="Your name" {...register("name")} data-testid="input-contact-name" />
                  {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" type="email" placeholder="you@company.com" {...register("email")} data-testid="input-contact-email" />
                  {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
                </div>
                <div className="space-y-2">
                  <Label>Subject</Label>
                  <Select value={watch("subject")} onValueChange={(v) => setValue("subject", v)}>
                    <SelectTrigger data-testid="select-contact-subject">
                      <SelectValue placeholder="Select a subject" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="General Inquiry">General Inquiry</SelectItem>
                      <SelectItem value="Sales">Sales</SelectItem>
                      <SelectItem value="Support">Support</SelectItem>
                      <SelectItem value="Partnership">Partnership</SelectItem>
                    </SelectContent>
                  </Select>
                  {errors.subject && <p className="text-xs text-destructive">{errors.subject.message}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="message">Message</Label>
                  <Textarea id="message" placeholder="How can we help?" className="min-h-[120px]" {...register("message")} data-testid="input-contact-message" />
                  {errors.message && <p className="text-xs text-destructive">{errors.message.message}</p>}
                </div>
                <Button type="submit" disabled={submitting} className="w-full" data-testid="button-contact-submit">
                  {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Send Message
                </Button>
              </form>
            </div>

            <div className="space-y-6">
              <h2 className="text-lg font-semibold text-foreground">Contact info</h2>
              <div className="space-y-4">
                <div className="flex items-start gap-3 rounded-lg border bg-card p-4">
                  <Mail className="mt-0.5 h-5 w-5 text-primary shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-foreground">Email</p>
                    <p className="text-sm text-muted-foreground">hello@founderconsole.ai</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 rounded-lg border bg-card p-4">
                  <Clock className="mt-0.5 h-5 w-5 text-primary shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-foreground">Response time</p>
                    <p className="text-sm text-muted-foreground">Within 24 hours on business days</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 rounded-lg border bg-card p-4">
                  <MessageSquare className="mt-0.5 h-5 w-5 text-primary shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-foreground">Office hours</p>
                    <p className="text-sm text-muted-foreground">Mon–Fri, 9am–6pm PT</p>
                  </div>
                </div>
              </div>

              <div className="mt-8">
                <h3 className="text-sm font-semibold text-foreground mb-3">Quick answers</h3>
                <Accordion type="single" collapsible className="space-y-2">
                  {contactFaq.map((item, i) => (
                    <AccordionItem key={i} value={`faq-${i}`} className="rounded-lg border bg-card px-4">
                      <AccordionTrigger className="text-sm font-medium text-foreground hover:no-underline">
                        {item.question}
                      </AccordionTrigger>
                      <AccordionContent className="text-sm text-muted-foreground">
                        {item.answer}
                      </AccordionContent>
                    </AccordionItem>
                  ))}
                </Accordion>
              </div>
            </div>
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
