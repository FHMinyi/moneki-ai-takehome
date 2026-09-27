export type TrendReference = Readonly<{
  type: 'daily_trend';
  start: string;
  end: string;
  store_id: string | null;
  metric: 'net_revenue';
}>;

export type TrendAttachment = Readonly<{ id: string; context: TrendReference; storeLabel: string }>;
