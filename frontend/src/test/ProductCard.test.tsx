import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import ProductCard from "../components/ProductCard";

describe("ProductCard", () => {
  it("shows the product and formatted INR price", () => {
    render(<MemoryRouter><ProductCard product={{ id: 1, category_id: 1, category_name: "Home", name: "Luma Lamp", slug: "luma-lamp", sku: "L-1", description: "Light", price: "2499.00", currency: "INR", stock: 4, sales_count: 0 }}/></MemoryRouter>);
    expect(screen.getByText("Luma Lamp")).toBeInTheDocument();
    expect(screen.getByText(/2,499/)).toBeInTheDocument();
  });
});
