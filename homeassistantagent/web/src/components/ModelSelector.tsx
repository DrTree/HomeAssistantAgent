interface ModelSelectorProps {
  modelOptions: string[];
  selectedModel: string;
  onChange: (value: string) => void;
  debugMessages: boolean;
  onDebugChange: (value: boolean) => void;
}

export function ModelSelector({
  modelOptions,
  selectedModel,
  onChange,
  debugMessages,
  onDebugChange,
}: ModelSelectorProps) {
  return (
    <section className="controls">
      <label className="controls__label" htmlFor="model-select">
        Model
      </label>
      <select
        id="model-select"
        className="controls__select"
        value={selectedModel}
        onChange={(event) => onChange(event.target.value)}
      >
        {modelOptions.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
      <label className="controls__toggle" htmlFor="debug-messages">
        <input
          id="debug-messages"
          className="controls__checkbox"
          type="checkbox"
          checked={debugMessages}
          onChange={(event) => onDebugChange(event.target.checked)}
        />
        Log messages
      </label>
    </section>
  );
}
