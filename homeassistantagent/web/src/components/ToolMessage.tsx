import { type UIMessage, isToolUIPart } from 'ai';
import { parseCalculatorInput } from './toolUtils';

export type ToolOutputPayload =
  | {
      tool: string;
      toolCallId: string;
      output: unknown;
      state?: 'output-available';
      errorText?: never;
    }
  | {
      tool: string;
      toolCallId: string;
      output?: never;
      state: 'output-error';
      errorText: string;
    };

type ToolMessageProps = {
  part: UIMessage['parts'][number];
  addToolOutput: (payload: ToolOutputPayload) => void;
};

export const ToolMessage = ({ part, addToolOutput }: ToolMessageProps) => {
  if (!isToolUIPart(part)) {
    return null;
  }

  if (part.type !== 'tool-calculator') {
    return (
      <div className="chat__tool">
        <p className="chat__tool-title">Tool request</p>
        <pre className="chat__tool-details">{JSON.stringify(part, null, 2)}</pre>
      </div>
    );
  }

  const parsedInput = parseCalculatorInput(part.input);

  if (part.state === 'approval-requested' || part.state === 'input-available') {
    return (
      <div className="chat__tool">
        <p className="chat__tool-title">Calculator approval requested</p>
        <p className="chat__tool-details">
          {parsedInput.number_a} {parsedInput.operator} {parsedInput.number_b}
        </p>
        <div className="chat__tool-actions">
          <button
            type="button"
            className="chat__tool-button"
            onClick={() => {
              if (
                typeof parsedInput.number_a !== 'number' ||
                typeof parsedInput.number_b !== 'number' ||
                !parsedInput.operator
              ) {
                addToolOutput({
                  tool: 'calculator',
                  toolCallId: part.toolCallId,
                  state: 'output-error',
                  errorText: 'Missing calculator inputs.',
                });
                return;
              }

              if (parsedInput.operator === '/' && parsedInput.number_b === 0) {
                addToolOutput({
                  tool: 'calculator',
                  toolCallId: part.toolCallId,
                  state: 'output-error',
                  errorText: 'Cannot divide by zero.',
                });
                return;
              }

              const result =
                parsedInput.operator === '+'
                  ? parsedInput.number_a + parsedInput.number_b
                  : parsedInput.operator === '-'
                    ? parsedInput.number_a - parsedInput.number_b
                    : parsedInput.operator === '*'
                      ? parsedInput.number_a * parsedInput.number_b
                      : parsedInput.number_a / parsedInput.number_b;

              addToolOutput({
                tool: 'calculator',
                toolCallId: part.toolCallId,
                output: result,
              });
            }}
          >
            Approve
          </button>
          <button
            type="button"
            className="chat__tool-button chat__tool-button--deny"
            onClick={() =>
              addToolOutput({
                tool: 'calculator',
                toolCallId: part.toolCallId,
                state: 'output-error',
                errorText: 'Calculator request denied by user.',
              })
            }
          >
            Deny
          </button>
        </div>
      </div>
    );
  }

  if (
    (part.state === 'approval-responded' && part.approval.approved === false) ||
    part.state === 'output-denied'
  ) {
    return (
      <div className="chat__tool">
        <p className="chat__tool-title">Calculator request denied</p>
        <p className="chat__tool-details">
          {parsedInput.number_a} {parsedInput.operator} {parsedInput.number_b}
        </p>
      </div>
    );
  }

  if (part.state === 'output-available') {
    return (
      <div className="chat__tool">
        <p className="chat__tool-title">Calculator result</p>
        <p className="chat__tool-details">
          {parsedInput.number_a} {parsedInput.operator} {parsedInput.number_b} = {part.output as number}
        </p>
      </div>
    );
  }

  if (part.state === 'output-error') {
    const errorText = part.errorText ?? 'Unable to process calculator request.';
    const isDenied = errorText.toLowerCase().includes('denied');
    return (
      <div className="chat__tool">
        <p className="chat__tool-title">{isDenied ? 'Calculator request denied' : 'Calculator error'}</p>
        <p className="chat__tool-details">
          {parsedInput.number_a} {parsedInput.operator} {parsedInput.number_b}
        </p>
        <p className="chat__tool-details">{errorText}</p>
      </div>
    );
  }

  if (part.state === 'input-streaming') {
    return (
      <div className="chat__tool">
        <p className="chat__tool-title">Calculator request incoming…</p>
      </div>
    );
  }

  return (
    <div className="chat__tool">
      <p className="chat__tool-title">Calculator pending</p>
    </div>
  );
};
