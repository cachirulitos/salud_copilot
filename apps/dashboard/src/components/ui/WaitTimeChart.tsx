import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const AREA_COLORS: Record<string, string> = {
  "Área de Laboratorio": "#008A4B",
  "Área de Ultrasonido": "#005B9F",
  "Área de Rayos X": "#F6AD55",
  "Área de Electrocardiograma": "#9F7AEA",
};

interface WaitTimeChartProps {
  history: {
    labels: string[];
    series: Record<string, number[]>;
  };
}

export default function WaitTimeChart({ history }: WaitTimeChartProps) {
  // Transform data format for Recharts
  const data = history.labels.map((label, index) => {
    const dataPoint: any = { time: label };
    Object.keys(history.series).forEach((area) => {
      dataPoint[area] = history.series[area][index];
    });
    return dataPoint;
  });

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer
        width="100%"
        height="100%"
        minWidth={100}
        minHeight={100}>
        <LineChart
          data={data}
          margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#2A2D3A"
            vertical={false}
          />
          <XAxis
            dataKey="time"
            tick={{ fill: "var(--color-content-secondary)", fontSize: 12 }}
            axisLine={{ stroke: "var(--color-surface-border)" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "var(--color-content-secondary)", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1A1D27",
              borderColor: "#2A2D3A",
              color: "#d1d5db",
              borderRadius: "0.5rem",
            }}
            formatter={(value: any, name: any, props: any) => {
              return [`${value} min`, name] as [string, string];
            }}
          />
          <Legend
            verticalAlign="bottom"
            height={36}
            iconType="circle"
            wrapperStyle={{ paddingTop: "10px" }}
          />
          {Object.keys(history.series).map((area) => (
            <Line
              key={area}
              type="monotone"
              dataKey={area}
              stroke={AREA_COLORS[area] || "#cccccc"}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 6, strokeWidth: 0 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
