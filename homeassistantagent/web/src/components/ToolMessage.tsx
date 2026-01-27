import { type UIMessage, isToolUIPart } from 'ai';
import type { ReactNode } from 'react';
import { parseCalculatorInput } from './toolUtils';

export type ToolOutputPayload =
  | {
      toolCallId: string;
      output: {
        approved: true;
      };
    }
  | {
      toolCallId: string;
      output: {
        approved: false;
        reason: string;
      };
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
                addToolOutput({
                  toolCallId: part.toolCallId,
                  output: { approved: true },
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
                  toolCallId: part.toolCallId,
                  output: { approved: false, reason: 'User denied' },
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
    return (
      <ToolCard title={`${toolName} result`}>
        {renderToolSummary(part, renderer)}
        {renderToolOutput(part, renderer)}
      </ToolCard>
    );
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
