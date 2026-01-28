import { createContext, useContext, type ReactNode } from 'react';

type SendMessage = (
  message?: { text: string },
  options?: {
    body?: {
      deferredToolResults?: {
        approvals?: Record<string, boolean>;
      };
    };
  },
) => Promise<void>;

type ApprovalContextValue = {
  approve: (toolCallId: string) => Promise<void>;
  deny: (toolCallId: string) => Promise<void>;
};

const ApprovalContext = createContext<ApprovalContextValue | null>(null);

export const ApprovalProvider = ({
  sendMessage,
  children,
}: {
  sendMessage: SendMessage;
  children: ReactNode;
}) => {
  const approve = (toolCallId: string) =>
    sendMessage(undefined, {
      body: {
        deferredToolResults: {
          approvals: {
            [toolCallId]: true,
          },
        },
      },
    });

  const deny = (toolCallId: string) =>
    sendMessage(undefined, {
      body: {
        deferredToolResults: {
          approvals: {
            [toolCallId]: false,
          },
        },
      },
    });

  return (
    <ApprovalContext.Provider value={{ approve, deny }}>
      {children}
    </ApprovalContext.Provider>
  );
};

export const useApproval = () => {
  const context = useContext(ApprovalContext);
  if (!context) {
    throw new Error('useApproval must be used within an ApprovalProvider');
  }
  return context;
};
