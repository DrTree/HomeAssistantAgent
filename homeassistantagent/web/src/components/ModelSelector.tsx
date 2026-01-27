interface ModelSelectorProps {
  modelOptions: string[];
  selectedModel: string;
  onChange: (value: string) => void;
}

export function ModelSelector({ modelOptions, selectedModel, onChange }: ModelSelectorProps) {
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
    </section>
  );
}
