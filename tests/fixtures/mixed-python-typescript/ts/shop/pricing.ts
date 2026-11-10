/** Computes prices. */
// aio-sdlc-node: 22222222-2222-4222-8222-222222222222
export class PriceCalculator {
  rate: number;

  constructor() {
    this.rate = 1;
  }

  total(amount: number): number {
    return amount * this.rate;
  }

  private rounding(value: number): number {
    return value;
  }
}

export function formatPrice(value: number): string {
  return String(value);
}

export interface PriceRule {
  apply(value: number): number;
}

export type Currency = "CAD" | "USD";

export enum Rounding {
  Up,
  Down,
}
