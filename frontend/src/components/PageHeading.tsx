import { useEffect, useRef } from "react";

export function PageHeading({ title, description }: { title: string; description: string }) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus(); }, []);
  return <header className="page-heading">
    <h1 tabIndex={-1} ref={heading}>{title}</h1><p>{description}</p>
  </header>;
}
