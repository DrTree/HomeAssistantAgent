import { type UIMessage, isToolUIPart } from 'ai';
import { type ReactNode, useMemo, useState } from 'react';
import { parseCalculatorInput } from './toolUtils';
import { useApproval } from '../hooks/useApproval';

type ToolMessageProps = {
  part: UIMessage['parts'][number];
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
    if (typeof part.output !== 'number') {
      return <ToolJsonFallback value={part.output} />;
    }

    const parsedInput = parseCalculatorInput(part.input);
    return (
      <ToolDetails>
        {parsedInput.number_a} {parsedInput.operator} {parsedInput.number_b} = {part.output}
      </ToolDetails>
    );
  },
};

const toolRenderers: Record<string, ToolRenderer> = {
  //calculator: calculatorRenderer,
};

const renderToolInput = (part: ToolPart, renderer?: ToolRenderer) => {
  if (renderer?.renderInput) {
    return renderer.renderInput(part);
  }

  if (typeof part.input === 'string') {
    return <ToolDetails>{part.input}</ToolDetails>;
  }

  return <ToolJsonFallback value={part.input} />;
};

const renderToolSummary = (part: ToolPart, renderer?: ToolRenderer) => {
  if (renderer?.renderSummary) {
    return renderer.renderSummary(part);
  }

  if (typeof part.input === 'string') {
    return <ToolDetails>{part.input}</ToolDetails>;
  }

  return <ToolJsonFallback value={part.input} />;
};

const renderToolOutput = (part: ToolPart, renderer?: ToolRenderer) => {
  if (renderer?.renderOutput) {
    return renderer.renderOutput(part);
  }

  if (typeof part.output === 'string') {
    return <ToolDetails>{part.output}</ToolDetails>;
  }

  return <ToolJsonFallback value={part.output} />;
};

const getToolText = (part: ToolPart) => {
  if (part.state === 'output-available') {
    if (typeof part.output === 'string') {
      return part.output;
    }

    if (part.output && typeof part.output === 'object' && 'text' in part.output) {
      const { text } = part.output as { text?: unknown };
      if (typeof text === 'string') {
        return text;
      }
    }
  }

  if (part.state === 'output-error') {
    return part.errorText ?? 'Unable to process tool request.';
  }

  return null;
};

const renderToolDetails = (part: ToolPart, renderer: ToolRenderer | undefined, toolName: string) => {
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

export const ToolMessage = ({ part }: ToolMessageProps) => {
  if (!isToolUIPart(part)) {
    return null;
  }

  const { approve, deny } = useApproval();
  const toolName = toolTypeToName(part);
  const renderer = toolRenderers[toolName];
  const [isExpanded, setIsExpanded] = useState(false);
  const toolText = useMemo(() => getToolText(part), [part]);

  if (part.state === 'approval-requested' || part.state === 'input-available') {
    return (
      <ToolCard
        title={`${toolName} approval requested`}
        actions={
          <div className="chat__tool-actions">
            <button
              type="button"
              className="chat__tool-button"
              onClick={async () => {
                await approve(part.toolCallId);
              }}
            >
              Approve
            </button>
            <button
              type="button"
              className="chat__tool-button chat__tool-button--deny"
              onClick={async () => {
                await deny(part.toolCallId);
              }}
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

  return (
    <>
      <button
        type="button"
        className="chat__tool-toggle"
        onClick={() => setIsExpanded((expanded) => !expanded)}
      >
        {toolText ?? `${toolName} tool details`}
      </button>
      {isExpanded ? renderToolDetails(part, renderer, toolName) : null}
    </>
  );
};
