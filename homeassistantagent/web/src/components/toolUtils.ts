import type { UIMessage } from 'ai';

export type CalculatorInput = {
  number_a?: number;
  number_b?: number;
  operator?: string;
};

export const parseCalculatorInput = (input: UIMessage['parts'][number]['input']): CalculatorInput => {
  if (typeof input === 'string') {
    try {
      return JSON.parse(input) as CalculatorInput;
    } catch (error) {
      console.warn('Unable to parse tool input.', error);
      return {};
    }
  }

  return (input ?? {}) as CalculatorInput;
};
