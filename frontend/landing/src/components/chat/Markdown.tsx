import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function Markdown({ children }: { children: string }) {
  return (
    <div className="prose-chat text-[15.5px] leading-[1.65] text-zurich-dark">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: (props) => (
            <a
              {...props}
              target="_blank"
              rel="noopener noreferrer"
              className="text-zurich-blue underline decoration-zurich-blue/30 underline-offset-4 hover:decoration-zurich-blue"
            />
          ),
          ul: (props) => <ul {...props} className="list-disc pl-6 my-3 space-y-1.5 marker:text-zurich-gray" />,
          ol: (props) => <ol {...props} className="list-decimal pl-6 my-3 space-y-1.5 marker:text-zurich-gray" />,
          li: (props) => <li {...props} className="pl-1" />,
          code: ({ className, children, ...rest }) => {
            const isBlock = String(className || "").includes("language-");
            if (isBlock) {
              return (
                <pre className="my-3 rounded-xl bg-zurich-navy text-zurich-off-white text-[13px] leading-relaxed p-4 overflow-x-auto">
                  <code {...rest}>{children}</code>
                </pre>
              );
            }
            return (
              <code className="rounded-md bg-chat-user px-1.5 py-0.5 text-[13.5px] font-mono text-zurich-dark">
                {children}
              </code>
            );
          },
          p: (props) => <p {...props} className="my-2.5 first:mt-0 last:mb-0" />,
          strong: (props) => <strong {...props} className="font-semibold text-zurich-dark" />,
          h1: (props) => <h3 {...props} className="text-lg font-semibold mt-4 mb-2" />,
          h2: (props) => <h3 {...props} className="text-base font-semibold mt-4 mb-2" />,
          h3: (props) => <h3 {...props} className="text-base font-semibold mt-4 mb-2" />,
          blockquote: (props) => (
            <blockquote {...props} className="border-l-2 border-chat-border pl-4 my-3 text-zurich-gray italic" />
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
