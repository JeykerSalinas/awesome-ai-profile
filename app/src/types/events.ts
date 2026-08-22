export type MessageDeltaData = {
  text: string;
};

export type MessageDeltaEvent = {
  event: "message_delta";
  data: MessageDeltaData;
};

export type DoneEvent = {
  event: "done";
  data: {};
};

export type ErrorEvent = {
  event: "error";
  data: {
    message: string;
  };
};

export type StreamEvent = MessageDeltaEvent | DoneEvent | ErrorEvent;

export const isStreamEvent = (value: unknown): value is StreamEvent => {
  if (!value || typeof value !== "object") {
    return false;
  }

  const event = (value as { event?: unknown }).event;
  const data = (value as { data?: unknown }).data;

  if (event === "message_delta") {
    return !!data && typeof (data as { text?: unknown }).text === "string";
  }

  if (event === "error") {
    return !!data && typeof (data as { message?: unknown }).message === "string";
  }

  return event === "done" && !!data && typeof data === "object";
};
