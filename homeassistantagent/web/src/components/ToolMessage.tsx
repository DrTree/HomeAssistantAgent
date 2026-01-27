import { type UIMessage, isToolUIPart } from 'ai';
import type { ReactNode } from 'react';
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

type ToolPart = Extract<UIMessage['parts'][number], { type: `tool-${string}` }>;

type ToolRenderer = {
  renderInput: (part: ToolPart) => ReactNode;
  renderSummary?: (part: ToolPart) => ReactNode;
  renderOutput?: (part: ToolPart) => ReactNode;
  handleApprove?: (part: ToolPart) => ToolOutputPayload;
};

const ToolCard = ({
  title,
  children,
  actions,
}: {
  title: string;
  children?: ReactNode;
  actions?: ReactNode;
}) => (
  <div className="chat__tool">
    <p className="chat__tool-title">{title}</p>
    {children}
    {actions}
  </div>
);

const ToolDetails = ({ children }: { children: ReactNode }) => (
  <p className="chat__tool-details">{children}</p>
);

const ToolJsonFallback = ({ value }: { value: unknown }) => (
  <pre className="chat__tool-details">{JSON.stringify(value, null, 2)}</pre>
);

const toolTypeToName = (part: ToolPart) => part.type.replace(/^tool-/, '');

const calculatorRenderer: ToolRenderer = {
  renderInput: (part) => {
    const parsedInput = parseCalculatorInput(part.input);
    return (
      <ToolDetails>
        {parsedInput.number_a} {parsedInput.operator} {parsedInput.number_b}
      </ToolDetails>
    );
  },
  renderSummary: (part) => {
    const parsedInput = parseCalculatorInput(part.input);
    return (
      <ToolDetails>
        {parsedInput.number_a} {parsedInput.operator} {parsedInput.number_b}
      </ToolDetails>
    );
  },
  renderOutput: (part) => {
    const parsedInput = parseCalculatorInput(part.input);
    return (
      <ToolDetails>
        {parsedInput.number_a} {parsedInput.operator} {parsedInput.number_b} ={' '}
        {part.output as number}
      </ToolDetails>
    );
  },
  handleApprove: (part) => {
    const parsedInput = parseCalculatorInput(part.input);

    if (
      typeof parsedInput.number_a !== 'number' ||
      typeof parsedInput.number_b !== 'number' ||
      !parsedInput.operator
    ) {
      return {
        tool: 'calculator',
        toolCallId: part.toolCallId,
        state: 'output-error',
        errorText: 'Missing calculator inputs.',
      };
    }

    if (parsedInput.operator === '/' && parsedInput.number_b === 0) {
      return {
        tool: 'calculator',
        toolCallId: part.toolCallId,
        state: 'output-error',
        errorText: 'Cannot divide by zero.',
      };
    }

    const result =
      parsedInput.operator === '+'
        ? parsedInput.number_a + parsedInput.number_b
        : parsedInput.operator === '-'
          ? parsedInput.number_a - parsedInput.number_b
          : parsedInput.operator === '*'
            ? parsedInput.number_a * parsedInput.number_b
            : parsedInput.number_a / parsedInput.number_b;

    return {
      tool: 'calculator',
      toolCallId: part.toolCallId,
      output: result,
    };
  },
};

const toolRenderers: Record<string, ToolRenderer> = {
  calculator: calculatorRenderer,
};

const renderToolInput = (part: ToolPart, renderer?: ToolRenderer) => {
  if (renderer?.renderInput) {
    return renderer.renderInput(part);
  }

  return <ToolJsonFallback value={part.input} />;
};

const renderToolSummary = (part: ToolPart, renderer?: ToolRenderer) => {
  if (renderer?.renderSummary) {
    return renderer.renderSummary(part);
  }

  return <ToolJsonFallback value={part.input} />;
};

const renderToolOutput = (part: ToolPart, renderer?: ToolRenderer) => {
  if (renderer?.renderOutput) {
    return renderer.renderOutput(part);
  }

  return <ToolJsonFallback value={part.output} />;
};

export const ToolMessage = ({ part, addToolOutput }: ToolMessageProps) => {
  if (!isToolUIPart(part)) {
    return null;
  }

  const toolName = toolTypeToName(part);
  const renderer = toolRenderers[toolName];

  if (part.state === 'approval-requested' || part.state === 'input-available') {
    return (
      <ToolCard
        title={`${toolName} approval requested`}
        actions={
          <div className="chat__tool-actions">
            <button
              type="button"
              className="chat__tool-button"
              onClick={() => {
                const payload =
                  renderer?.handleApprove?.(part) ??
                  ({
                    tool: toolName,
                    toolCallId: part.toolCallId,
                    state: 'output-error',
                    errorText: `No renderer available for ${toolName}.`,
                  } satisfies ToolOutputPayload);
                addToolOutput(payload);
              }}
            >
              Approve
            </button>
            <button
              type="button"
              className="chat__tool-button chat__tool-button--deny"
              onClick={() =>
                addToolOutput({
                  tool: toolName,
                  toolCallId: part.toolCallId,
                  state: 'output-error',
                  errorText: `${toolName} request denied by user.`,
                })
              }
            >
              Deny
            </button>
          </div>
        }
      >
        {renderToolInput(part, renderer)}
      </ToolCard>
    );
  }

  if (
    (part.state === 'approval-responded' && part.approval.approved === false) ||
    part.state === 'output-denied'
  ) {
    return (
      <ToolCard title={`${toolName} request denied`}>{renderToolSummary(part, renderer)}</ToolCard>
    );
  }

  if (part.state === 'output-available') {
    return <ToolCard title={`${toolName} result`}>{renderToolOutput(part, renderer)}</ToolCard>;
  }

  if (part.state === 'output-error') {
    const errorText = part.errorText ?? 'Unable to process tool request.';
    const isDenied = errorText.toLowerCase().includes('denied');
    return (
      <ToolCard title={isDenied ? `${toolName} request denied` : `${toolName} error`}>
        {renderToolSummary(part, renderer)}
        <ToolDetails>{errorText}</ToolDetails>
      </ToolCard>
    );
  }

  if (part.state === 'input-streaming') {
    return <ToolCard title={`${toolName} request incoming…`} />;
  }

  return <ToolCard title={`${toolName} pending`} />;
};
