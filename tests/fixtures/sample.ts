/**
 * Billing helpers for the fixture project.
 * @module billing
 */

export interface Invoice {
  id: string;
  total: number;
  paid?: boolean;
  currency: string;
}

export enum InvoiceStatus {
  Draft,
  Sent,
  Paid,
}

export type Money = { amount: number; currency: string };

/**
 * Format a money amount for display.
 * @param money - the amount to format
 * @returns the formatted string
 */
export function formatMoney(money: Money, locale: string = "en-CA"): string {
  return `${money.currency} ${money.amount.toFixed(2)} (${locale})`;
}

/** A service that creates invoices. */
export class InvoiceService {
  private counter: number = 0;
  readonly name: string = "invoices";

  constructor(private readonly prefix: string = "INV") {}

  /** Create a new invoice. */
  async createInvoice(total: number, currency: string): Promise<Invoice> {
    this.counter += 1;
    return { id: `${this.prefix}-${this.counter}`, total, currency };
  }

  static describe(): string {
    return "InvoiceService creates invoices";
  }

  get size(): number {
    return this.counter;
  }
}

export const defaultLocale = "en-CA";

export const summarize = (invoice: Invoice): string =>
  `${invoice.id}: ${invoice.total}`;
