import React from "react";

interface BrandMarkProps {
  className: string;
}

/** Small app mark. The image is decorative; the nearby title carries the name. */
export function BrandMark({ className }: BrandMarkProps) {
  return (
    <span className={className}>
      <img className="brand-mark-image" src="/brand-mark.png" alt="" width={128} height={128} />
    </span>
  );
}
