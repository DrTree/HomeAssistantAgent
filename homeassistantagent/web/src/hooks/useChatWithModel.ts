import { useChat, type UseChatHelpers, type UseChatOptions } from '@ai-sdk/react';
import type { UIMessage } from 'ai';

type UseChatWithModelOptions<UI_MESSAGE extends UIMessage> = UseChatOptions<UI_MESSAGE> & {
  model?: string;
};

export function useChatWithModel<UI_MESSAGE extends UIMessage = UIMessage>({
  model,
  ...options
}: UseChatWithModelOptions<UI_MESSAGE>): UseChatHelpers<UI_MESSAGE> {
  const chat = useChat<UI_MESSAGE>(options);

  const sendMessage: typeof chat.sendMessage = (message, requestOptions) => {
    if (!model) {
      return chat.sendMessage(message as any, requestOptions);
    }

    const body = requestOptions?.body ?? {};
    const bodyWithModel = 'model' in body ? body : { ...body, model };

    if (bodyWithModel === body) {
      return chat.sendMessage(message as any, requestOptions);
    }

    return chat.sendMessage(message as any, { ...requestOptions, body: bodyWithModel });
  };

  return { ...chat, sendMessage };
}
