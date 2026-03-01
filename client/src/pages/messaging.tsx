import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { queryClient, apiRequest } from "@/lib/queryClient";
import { getErrorMessage } from "@/lib/errors";
import {
  MessageSquare,
  Phone,
  Send,
  Clock,
  ArrowUpRight,
  ArrowDownLeft,
  CheckCircle2,
  XCircle,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { SiWhatsapp } from "react-icons/si";

export default function MessagingPage() {
  const { toast } = useToast();
  const [smsTo, setSmsTo] = useState("");
  const [smsBody, setSmsBody] = useState("");
  const [waTo, setWaTo] = useState("");
  const [waBody, setWaBody] = useState("");
  const [activeTab, setActiveTab] = useState("sms");

  const statusQuery = useQuery<{ configured: boolean }>({
    queryKey: ["/api/messaging/status"],
  });

  const historyQuery = useQuery<{ success: boolean; messages: any[] }>({
    queryKey: ["/api/messaging/history"],
    enabled: statusQuery.data?.configured === true,
    refetchInterval: 30000,
  });

  const smsMutation = useMutation({
    mutationFn: async (data: { to: string; body: string }) => {
      const res = await apiRequest("POST", "/api/messaging/sms", data);
      return res.json();
    },
    onSuccess: (data) => {
      if (data.success) {
        toast({ title: "SMS Sent", description: `Message delivered to ${smsTo}` });
        setSmsBody("");
        queryClient.invalidateQueries({ queryKey: ["/api/messaging/history"] });
      } else {
        toast({ title: "Failed", description: getErrorMessage(data.error, 'SMS delivery failed'), variant: "destructive" });
      }
    },
    onError: (error: unknown) => {
      toast({ title: "Error", description: getErrorMessage(error, 'Failed to send SMS'), variant: "destructive" });
    },
  });

  const whatsappMutation = useMutation({
    mutationFn: async (data: { to: string; body: string }) => {
      const res = await apiRequest("POST", "/api/messaging/whatsapp", data);
      return res.json();
    },
    onSuccess: (data) => {
      if (data.success) {
        toast({ title: "WhatsApp Sent", description: `Message delivered to ${waTo}` });
        setWaBody("");
        queryClient.invalidateQueries({ queryKey: ["/api/messaging/history"] });
      } else {
        toast({ title: "Failed", description: getErrorMessage(data.error, 'WhatsApp delivery failed'), variant: "destructive" });
      }
    },
    onError: (error: unknown) => {
      toast({ title: "Error", description: getErrorMessage(error, 'Failed to send WhatsApp message'), variant: "destructive" });
    },
  });

  const handleSendSms = () => {
    if (!smsTo || !smsBody) return;
    smsMutation.mutate({ to: smsTo, body: smsBody });
  };

  const handleSendWhatsApp = () => {
    if (!waTo || !waBody) return;
    whatsappMutation.mutate({ to: waTo, body: waBody });
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return "";
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "delivered":
        return <Badge variant="secondary" className="bg-emerald-500/20 text-emerald-400"><CheckCircle2 className="h-3 w-3 mr-1" />Delivered</Badge>;
      case "sent":
        return <Badge variant="secondary" className="bg-blue-500/20 text-blue-400"><Send className="h-3 w-3 mr-1" />Sent</Badge>;
      case "failed":
      case "undelivered":
        return <Badge variant="destructive"><XCircle className="h-3 w-3 mr-1" />Failed</Badge>;
      case "queued":
        return <Badge variant="secondary"><Clock className="h-3 w-3 mr-1" />Queued</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  if (statusQuery.isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!statusQuery.data?.configured) {
    return (
      <div className="p-6 max-w-2xl mx-auto">
        <Card>
          <CardContent className="p-8 text-center">
            <MessageSquare className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <h2 className="text-xl font-semibold mb-2">Twilio Not Connected</h2>
            <p className="text-muted-foreground mb-4">
              Connect your Twilio account in the Integrations page to start sending SMS and WhatsApp messages.
            </p>
            <Button variant="outline" asChild data-testid="button-go-integrations">
              <a href="/integrations">Go to Integrations</a>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold" data-testid="text-messaging-title">Messaging</h1>
          <p className="text-muted-foreground text-sm mt-1">Send SMS and WhatsApp messages to customers</p>
        </div>
        <Badge variant="secondary" className="bg-emerald-500/20 text-emerald-400">
          <CheckCircle2 className="h-3 w-3 mr-1" />
          Twilio Connected
        </Badge>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList data-testid="tabs-messaging-type">
          <TabsTrigger value="sms" data-testid="tab-sms">
            <Phone className="h-4 w-4 mr-1.5" />
            SMS
          </TabsTrigger>
          <TabsTrigger value="whatsapp" data-testid="tab-whatsapp">
            <SiWhatsapp className="h-4 w-4 mr-1.5" />
            WhatsApp
          </TabsTrigger>
          <TabsTrigger value="history" data-testid="tab-history">
            <Clock className="h-4 w-4 mr-1.5" />
            History
          </TabsTrigger>
        </TabsList>

        <TabsContent value="sms" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Phone className="h-5 w-5" />
                Send SMS
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium text-muted-foreground mb-1.5 block">Phone Number</label>
                <Input
                  placeholder="+1 (555) 123-4567"
                  value={smsTo}
                  onChange={(e) => setSmsTo(e.target.value)}
                  data-testid="input-sms-to"
                />
                <p className="text-xs text-muted-foreground mt-1">Include country code (e.g. +1 for US)</p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground mb-1.5 block">Message</label>
                <Textarea
                  placeholder="Type your message here..."
                  value={smsBody}
                  onChange={(e) => setSmsBody(e.target.value)}
                  className="min-h-[120px] resize-none"
                  data-testid="input-sms-body"
                />
                <p className="text-xs text-muted-foreground mt-1">{smsBody.length} / 160 characters (1 segment)</p>
              </div>
              <Button
                onClick={handleSendSms}
                disabled={!smsTo || !smsBody || smsMutation.isPending}
                data-testid="button-send-sms"
              >
                {smsMutation.isPending ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Send className="h-4 w-4 mr-2" />
                )}
                Send SMS
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="whatsapp" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <SiWhatsapp className="h-5 w-5 text-green-500" />
                Send WhatsApp Message
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium text-muted-foreground mb-1.5 block">Phone Number</label>
                <Input
                  placeholder="+1 (555) 123-4567"
                  value={waTo}
                  onChange={(e) => setWaTo(e.target.value)}
                  data-testid="input-whatsapp-to"
                />
                <p className="text-xs text-muted-foreground mt-1">Include country code (e.g. +91 for India)</p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground mb-1.5 block">Message</label>
                <Textarea
                  placeholder="Type your WhatsApp message here..."
                  value={waBody}
                  onChange={(e) => setWaBody(e.target.value)}
                  className="min-h-[120px] resize-none"
                  data-testid="input-whatsapp-body"
                />
              </div>
              <Button
                onClick={handleSendWhatsApp}
                disabled={!waTo || !waBody || whatsappMutation.isPending}
                className="bg-green-600 border-green-600"
                data-testid="button-send-whatsapp"
              >
                {whatsappMutation.isPending ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <SiWhatsapp className="h-4 w-4 mr-2" />
                )}
                Send WhatsApp
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history" className="mt-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Clock className="h-5 w-5" />
                  Message History
                </CardTitle>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => queryClient.invalidateQueries({ queryKey: ["/api/messaging/history"] })}
                  data-testid="button-refresh-history"
                >
                  <RefreshCw className="h-4 w-4 mr-1.5" />
                  Refresh
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {historyQuery.isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                </div>
              ) : !historyQuery.data?.messages?.length ? (
                <div className="text-center py-8 text-muted-foreground">
                  <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No messages yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {historyQuery.data.messages.map((msg: any) => (
                    <div
                      key={msg.sid}
                      className="flex items-start gap-3 p-3 rounded-lg border"
                      data-testid={`message-${msg.sid}`}
                    >
                      <div className="mt-0.5">
                        {msg.direction?.includes("outbound") ? (
                          <ArrowUpRight className="h-4 w-4 text-blue-400" />
                        ) : (
                          <ArrowDownLeft className="h-4 w-4 text-emerald-400" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-medium font-mono">
                            {msg.direction?.includes("outbound") ? msg.to : msg.from}
                          </span>
                          {getStatusBadge(msg.status)}
                          {msg.to?.startsWith("whatsapp:") && (
                            <Badge variant="outline" className="text-green-500 border-green-500/30">
                              <SiWhatsapp className="h-3 w-3 mr-1" />
                              WhatsApp
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground mt-1 break-words">{msg.body}</p>
                        <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                          <span>{formatDate(msg.dateSent || msg.dateCreated)}</span>
                          {msg.price && (
                            <span>
                              {msg.price} {msg.priceUnit}
                            </span>
                          )}
                          <span className="font-mono text-[10px] opacity-60">{msg.sid?.slice(0, 12)}...</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
