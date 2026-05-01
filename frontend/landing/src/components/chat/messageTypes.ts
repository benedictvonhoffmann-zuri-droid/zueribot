// Loose structural types for assistant-ui message content.
//
// The SDK's own types (ThreadMessage, MessageContentPart) are precise but
// drift between versions; we only need the shape we actually read.

export type TextPart = { type: "text"; text: string };

// Any other block (tool_use, image, etc.) — we keep it open so a chunk
// from a future SDK release won't break the type.
export type ContentPart = TextPart | { type: string; [k: string]: unknown };

export type MessageLike = {
  role: string;
  content?: readonly ContentPart[] | ContentPart[];
};

export function isTextPart(p: ContentPart): p is TextPart {
  return p.type === "text" && typeof (p as TextPart).text === "string";
}
