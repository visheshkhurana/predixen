import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import type { MonthlyProjection } from "@shared/schema";
import { cn, formatCurrencyFull } from "@/lib/utils";

interface DataTableProps {
  projections: MonthlyProjection[];
  title?: string;
  currency?: string;
}

export function DataTable({ projections, title = "Monthly Projections", currency = 'USD' }: DataTableProps) {

  return (
    <Card data-testid="table-projections">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">{title}</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="w-full">
          <div className="min-w-[600px]">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[100px]">Month</TableHead>
                  <TableHead className="text-right">Revenue</TableHead>
                  <TableHead className="text-right">Expenses</TableHead>
                  <TableHead className="text-right">Net Burn</TableHead>
                  <TableHead className="text-right">Cash Balance</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {projections.map((projection, index) => (
                  <TableRow
                    key={projection.month}
                    className={cn(
                      projection.cashBalance <= 0 && "bg-red-50 dark:bg-red-950/20"
                    )}
                    data-testid={`row-projection-${index}`}
                  >
                    <TableCell className="font-medium">{projection.date}</TableCell>
                    <TableCell className="text-right font-mono text-emerald-600 dark:text-emerald-400">
                      {formatCurrencyFull(projection.revenue, currency)}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {formatCurrencyFull(projection.expenses, currency)}
                    </TableCell>
                    <TableCell
                      className={cn(
                        "text-right font-mono",
                        projection.netBurn > 0
                          ? "text-red-600 dark:text-red-400"
                          : "text-emerald-600 dark:text-emerald-400"
                      )}
                    >
                      {projection.netBurn > 0 ? "-" : "+"}
                      {formatCurrencyFull(Math.abs(projection.netBurn), currency)}
                    </TableCell>
                    <TableCell
                      className={cn(
                        "text-right font-mono font-medium",
                        projection.cashBalance <= 0
                          ? "text-red-600 dark:text-red-400"
                          : ""
                      )}
                    >
                      {formatCurrencyFull(Math.max(0, projection.cashBalance), currency)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <ScrollBar orientation="horizontal" />
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
