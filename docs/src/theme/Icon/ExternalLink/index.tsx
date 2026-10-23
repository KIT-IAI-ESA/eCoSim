import type { ReactNode } from "react";
import { translate } from "@docusaurus/Translate";
import type { Props } from "@theme/Icon/ExternalLink";
import styles from "./styles.module.css";

// arrow-square-out (phosphor icons) from easimov
export default function IconExternalLink({
  width = 16,
  height = 16,
}: Props): ReactNode {
  return (
    <svg
      viewBox="0 0 256 256"
      width={width}
      height={height}
      fill="currentColor"
      aria-label={translate({
        id: "theme.IconExternalLink.ariaLabel",
        message: "(opens in new tab)",
        description: "The ARIA label for the external link icon",
      })}
      className={styles.icon}
    >
      <path d="M228,104a12,12,0,0,1-24,0V69l-59.51,59.51a12,12,0,0,1-17-17L187,52H152a12,12,0,0,1,0-24h64a12,12,0,0,1,12,12Zm-44,24a12,12,0,0,0-12,12v64H52V84h64a12,12,0,0,0,0-24H48A20,20,0,0,0,28,80V208a20,20,0,0,0,20,20H176a20,20,0,0,0,20-20V140A12,12,0,0,0,184,128Z" />
    </svg>
  );
}
