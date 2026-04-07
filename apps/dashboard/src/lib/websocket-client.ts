export interface DashboardEvent {
  event: "visit_updated" | "queue_changed" | "wait_time_updated" | "alert";
  area_id: string;
  data: any;
}

export class DashboardWebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private clinicId: string | null = null;
  private eventCallback: ((e: DashboardEvent) => void) | null = null;
  private statusCallback: ((connected: boolean) => void) | null = null;
  private _isConnected: boolean = false;

  get isConnected(): boolean {
    return this._isConnected;
  }

  private setConnected(status: boolean) {
    this._isConnected = status;
    if (this.statusCallback) {
      this.statusCallback(status);
    }
  }

  connect(
    clinicId: string,
    onEvent: (e: DashboardEvent) => void,
    onStatusChange: (connected: boolean) => void,
  ): void {
    this.clinicId = clinicId;
    this.eventCallback = onEvent;
    this.statusCallback = onStatusChange;

    this.initWebSocket();
  }

  private initWebSocket() {
    if (!this.clinicId) return;

    // Clean up existing connection if any
    if (this.ws) {
      this.ws.close();
    }

    // Default to localhost for demo, in prod this would be your API URL
    const wsUrl = `ws://localhost:8000/ws/dashboard/${this.clinicId}`;
    console.log(`[WebSocket] Connecting to ${wsUrl}...`);

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log("[WebSocket] Connected successfully");
        this.setConnected(true);
        if (this.reconnectTimer) {
          clearTimeout(this.reconnectTimer);
          this.reconnectTimer = null;
        }
      };

      this.ws.onmessage = (message) => {
        try {
          const data = JSON.parse(message.data) as DashboardEvent;
          if (this.eventCallback) {
            this.eventCallback(data);
          }
        } catch (e) {
          console.error("[WebSocket] Failed to parse message", e);
        }
      };

      this.ws.onclose = () => {
        console.log("[WebSocket] Disconnected");
        this.setConnected(false);
        this.ws = null;
        this.scheduleReconnect();
      };

      this.ws.onerror = (error) => {
        console.error("[WebSocket] Error", error);
        // Error will also trigger onclose, which handles reconnect
      };
    } catch (e) {
      console.error("[WebSocket] Failed to create connection", e);
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return;

    console.log("[WebSocket] Reconnecting in 3 seconds...");
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.initWebSocket();
    }, 3000);
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      // Prevent reconnect schedule by removing listeners
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.close();
      this.ws = null;
    }

    this.setConnected(false);
    this.clinicId = null;
    this.eventCallback = null;
    this.statusCallback = null;
  }
}
