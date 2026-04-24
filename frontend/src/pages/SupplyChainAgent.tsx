import { useEffect, useState } from "react";
import { AlertTriangle, Brain, ChevronLeft, PackageCheck, Truck } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type SupplyAvailabilityRecord = {
  supply_id: number;
  item_name: string | null;
  supplier_name: string | null;
  inventory_available: number | null;
  unit_price_per_unit: number | null;
  notification: {
    triggered: boolean;
    message: string;
    threshold: number;
  };
};

type SupplyAvailabilityListResponse = {
  threshold: number;
  total_records: number;
  low_inventory_records: number;
  records: SupplyAvailabilityRecord[];
};

const SupplyChainAgent = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SupplyAvailabilityListResponse | null>(null);

  const fetchAvailability = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/api/supply-chain/availability`);
      if (!response.ok) {
        const payload = (await response.json().catch(() => ({}))) as { detail?: string };
        throw new Error(payload.detail ?? `Request failed (${response.status})`);
      }
      const payload = (await response.json()) as SupplyAvailabilityListResponse;
      setResult(payload);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Failed to check supply availability.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchAvailability();
  }, []);

  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_10%_2%,rgba(23,162,155,0.2),transparent_38%),radial-gradient(circle_at_90%_8%,rgba(56,189,248,0.14),transparent_36%),linear-gradient(180deg,rgba(240,250,250,0.98),rgba(233,245,244,0.98))]">
      <div className="pointer-events-none absolute -left-24 top-12 h-72 w-72 rounded-full bg-accent/15 blur-3xl" />
      <div className="pointer-events-none absolute -right-20 top-20 h-80 w-80 rounded-full bg-primary/15 blur-3xl" />

      <header className="sticky top-0 z-20 border-b border-border/80 bg-background/80 backdrop-blur-md">
        <div className="container max-w-7xl py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-11 h-11 rounded-xl bg-gradient-primary flex items-center justify-center shadow-glow">
              <Brain className="w-5 h-5 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-3xl leading-none text-foreground">Supply Chain Agent</h1>
              <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Inventory Availability Monitor</p>
            </div>
          </div>
          <Link
            to="/"
            className="inline-flex items-center gap-2 rounded-full border border-border bg-card/70 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-foreground hover:bg-card"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            Back to Landing
          </Link>
        </div>
      </header>

      <main className="container max-w-7xl py-10">
        <Card className="border-border/80 bg-card/85">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-2xl">
              <Truck className="h-5 w-5 text-primary" />
              Supply Record Availability Check
            </CardTitle>
            <CardDescription>
              Retrieves all records from `supply_record`, verifies inventory availability, and triggers restock alerts for ongoing finish items when inventory is below `1000`.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-end">
              <Button onClick={() => void fetchAvailability()} disabled={loading}>
                {loading ? "Refreshing..." : "Refresh Records"}
              </Button>
            </div>

            {error && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>Request failed</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {!error && loading && <p className="text-sm text-muted-foreground">Loading supply records...</p>}

            {result && (
              <div className="space-y-4">
                <Card className="bg-background/70">
                  <CardContent className="pt-6 text-sm">
                    <p>
                      <span className="font-semibold">Total Records:</span> {result.total_records}
                    </p>
                    <p>
                      <span className="font-semibold">Low Inventory Alerts:</span> {result.low_inventory_records}
                    </p>
                    <p className="text-muted-foreground">
                      Threshold rule: inventory available below {result.threshold} triggers restock notification.
                    </p>
                  </CardContent>
                </Card>

                <div className="grid gap-4 md:grid-cols-2">
                  {result.records.map((record) => (
                    <Card key={record.supply_id} className="bg-background/70">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-lg">Supply ID #{record.supply_id}</CardTitle>
                        <CardDescription>{record.item_name ?? "Unknown item"}</CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-3 text-sm">
                        <p><span className="font-semibold">Inventory Available:</span> {record.inventory_available ?? "-"}</p>
                        <p><span className="font-semibold">Supplier:</span> {record.supplier_name ?? "-"}</p>
                        <p>
                          <span className="font-semibold">Unit Price:</span>{" "}
                          {record.unit_price_per_unit != null ? `RM ${record.unit_price_per_unit.toFixed(2)}` : "-"}
                        </p>
                        <Alert variant={record.notification.triggered ? "destructive" : "default"}>
                          <PackageCheck className="h-4 w-4" />
                          <AlertTitle>
                            {record.notification.triggered ? "Restock Notification Triggered" : "Inventory Status OK"}
                          </AlertTitle>
                          <AlertDescription>{record.notification.message}</AlertDescription>
                        </Alert>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
};

export default SupplyChainAgent;
