import { useState } from "react";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from "@/components/ui/form";
import { useSEO } from "@/lib/seo";
import { useToast } from "@/hooks/use-toast";
import { Mail, Clock, Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

const contactSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().email("Please enter a valid email address"),
  subject: z.string().min(1, "Please select a subject"),
  message: z.string().min(10, "Message must be at least 10 characters"),
});

type ContactForm = z.infer<typeof contactSchema>;

export default function ContactPage() {
  useSEO({
    title: "Contact | FounderConsole",
    description: "Get in touch with the FounderConsole team. We respond within 24 hours.",
    path: "/contact",
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "ContactPage",
      name: "Contact FounderConsole",
      url: "https://founderconsole.ai/contact",
      description: "Get in touch with the FounderConsole team. We respond within 24 hours.",
    },
  });

  const { toast } = useToast();
  const [isPending, setIsPending] = useState(false);

  const form = useForm<ContactForm>({
    resolver: zodResolver(contactSchema),
    defaultValues: { name: "", email: "", subject: "", message: "" },
  });

  const onSubmit = async (data: ContactForm) => {
    setIsPending(true);
    try {
      const website = (document.getElementById("contact-website") as HTMLInputElement | null)?.value ?? "";
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...data, website }),
      });
      if (!res.ok) throw new Error(`contact ${res.status}`);
      toast({ title: "Message sent", description: "We'll get back to you within 24 hours." });
      form.reset();
    } catch {
      toast({
        title: "Message not sent",
        description: "Something went wrong. Please email hello@founderconsole.ai directly.",
        variant: "destructive",
      });
    } finally {
      setIsPending(false);
    }
  };

  return (
    <MarketingLayout>
      <section>
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl" data-testid="text-contact-title">
            Get in Touch
          </h1>
          <p className="mt-3 max-w-2xl text-lg text-muted-foreground" data-testid="text-contact-subtitle">
            Questions, feedback, or partnership inquiries — we'd love to hear from you.
          </p>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-10">
          <div className="grid gap-8 md:grid-cols-2">
            <div>
              <h2 className="text-lg font-semibold text-foreground" data-testid="text-form-heading">Send us a message</h2>
              <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="mt-6 space-y-4" data-testid="form-contact">
                  <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Name</FormLabel>
                        <FormControl>
                          <Input placeholder="Your name" {...field} data-testid="input-contact-name" />
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
                          <Input type="email" placeholder="you@company.com" {...field} data-testid="input-contact-email" />
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
                            <SelectTrigger data-testid="select-contact-subject">
                              <SelectValue placeholder="Select a subject" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="General Inquiry">General Inquiry</SelectItem>
                            <SelectItem value="Sales">Sales</SelectItem>
                            <SelectItem value="Support">Support</SelectItem>
                            <SelectItem value="Partnership">Partnership</SelectItem>
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
                          <Textarea placeholder="How can we help?" className="min-h-[120px]" {...field} data-testid="input-contact-message" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <input
                    id="contact-website"
                    name="website"
                    type="text"
                    tabIndex={-1}
                    autoComplete="off"
                    aria-hidden="true"
                    className="hidden"
                  />
                  <Button type="submit" disabled={isPending} className="w-full" data-testid="button-contact-submit">
                    {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Send Message
                  </Button>
                </form>
              </Form>
            </div>

            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-foreground" data-testid="text-info-heading">Contact info</h2>
              <div className="flex items-start gap-3 rounded-xl border bg-card/50 p-6" data-testid="card-email">
                <Mail className="mt-0.5 h-5 w-5 text-primary shrink-0" />
                <div>
                  <p className="text-sm font-semibold text-foreground">Email</p>
                  <a href="mailto:hello@founderconsole.ai" className="text-sm text-muted-foreground hover:text-foreground">hello@founderconsole.ai</a>
                </div>
              </div>
              <div className="flex items-start gap-3 rounded-xl border bg-card/50 p-6" data-testid="card-response-time">
                <Clock className="mt-0.5 h-5 w-5 text-primary shrink-0" />
                <div>
                  <p className="text-sm font-semibold text-foreground">Response Time</p>
                  <p className="text-sm text-muted-foreground">Within 24 hours</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
