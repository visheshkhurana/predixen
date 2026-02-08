// Twilio messaging API routes
import type { Router, Request, Response } from 'express';
import { sendSms, sendWhatsApp, getMessageHistory, isTwilioConfigured } from './service';

export function registerTwilioRoutes(router: Router): void {
  router.get('/status', async (_req: Request, res: Response) => {
    try {
      const configured = await isTwilioConfigured();
      res.json({ configured });
    } catch (error: any) {
      res.json({ configured: false, error: error.message });
    }
  });

  router.post('/sms', async (req: Request, res: Response) => {
    try {
      const { to, body } = req.body;

      if (!to || !body) {
        return res.status(400).json({ error: 'Phone number (to) and message body are required' });
      }

      const result = await sendSms({ to, body });
      res.json({ success: true, message: result });
    } catch (error: any) {
      console.error('SMS send error:', error);
      res.status(500).json({ success: false, error: error.message });
    }
  });

  router.post('/whatsapp', async (req: Request, res: Response) => {
    try {
      const { to, body } = req.body;

      if (!to || !body) {
        return res.status(400).json({ error: 'Phone number (to) and message body are required' });
      }

      const result = await sendWhatsApp({ to, body });
      res.json({ success: true, message: result });
    } catch (error: any) {
      console.error('WhatsApp send error:', error);
      res.status(500).json({ success: false, error: error.message });
    }
  });

  router.get('/history', async (req: Request, res: Response) => {
    try {
      const limit = parseInt(req.query.limit as string) || 20;
      const messages = await getMessageHistory(limit);
      res.json({ success: true, messages });
    } catch (error: any) {
      console.error('Message history error:', error);
      res.status(500).json({ success: false, error: error.message });
    }
  });
}
