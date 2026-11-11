import { PriceCalculator } from "./pricing";

export class Order extends Entity {
  submit(): number {
    return new PriceCalculator().total(1);
  }
}

export const createOrder = (): Order => new Order();
