export type User = { id: number; name: string; email: string; role: string; is_active: boolean; avatar_url?: string };
export type Category = { id: number; name: string; slug: string; description?: string };
export type Product = {
  id: number; category_id: number; category_name: string; name: string; slug: string; sku: string;
  description?: string; price: string; currency: string; stock: number; image_url?: string; sales_count: number;
};
export type ProductPage = { items: Product[]; page: number; page_size: number; total: number; pages: number };
export type CartItem = {
  id: number; product_id: number; name: string; sku: string; image_url?: string; unit_price: string;
  quantity: number; line_total: string; available_stock: number;
};
export type Cart = { id: number; items: CartItem[]; item_count: number; subtotal: string; currency: string };
export type Order = {
  order_number: string; subtotal: string; shipping_total: string; tax_total: string; total: string;
  currency: string; payment_status: string; order_status: string; shipping_address: Record<string, string>;
  created_at: string; items: Array<{ product_name: string; product_sku: string; quantity: number; unit_price: string; line_total: string }>;
};
export type AppNotification = { id: number; type: string; title: string; message: string; is_read: boolean; created_at: string };
