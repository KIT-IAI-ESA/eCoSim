import type { ReactNode } from "react";
import clsx from "clsx";
import { useColorMode } from "@docusaurus/theme-common";
import type { Props } from "@theme/Navbar/ColorModeToggle";
import styles from "./styles.module.css";

// light/dark button of easimov instead of docusaurus default
// page starts in system mode --> icons follow data-theme
const SUN =
  "M116,36V20a12,12,0,0,1,24,0V36a12,12,0,0,1-24,0Zm80,92a68,68,0,1,1-68-68A68.07,68.07,0,0,1,196,128Zm-24,0a44,44,0,1,0-44,44A44.05,44.05,0,0,0,172,128ZM51.51,68.49a12,12,0,1,0,17-17l-12-12a12,12,0,0,0-17,17Zm0,119-12,12a12,12,0,0,0,17,17l12-12a12,12,0,1,0-17-17ZM196,72a12,12,0,0,0,8.49-3.51l12-12a12,12,0,0,0-17-17l-12,12A12,12,0,0,0,196,72Zm8.49,115.51a12,12,0,0,0-17,17l12,12a12,12,0,0,0,17-17ZM48,128a12,12,0,0,0-12-12H20a12,12,0,0,0,0,24H36A12,12,0,0,0,48,128Zm80,80a12,12,0,0,0-12,12v16a12,12,0,0,0,24,0V220A12,12,0,0,0,128,208Zm108-92H220a12,12,0,0,0,0,24h16a12,12,0,0,0,0-24Z";
const MOON =
  "M236.37,139.4a12,12,0,0,0-12-3A84.07,84.07,0,0,1,119.6,31.59a12,12,0,0,0-15-15A108.86,108.86,0,0,0,49.69,55.07,108,108,0,0,0,136,228a107.09,107.09,0,0,0,64.93-21.69,108.86,108.86,0,0,0,38.44-54.94A12,12,0,0,0,236.37,139.4Zm-49.88,47.74A84,84,0,0,1,68.86,69.51,84.93,84.93,0,0,1,92.27,48.29Q92,52.13,92,56A108.12,108.12,0,0,0,200,164q3.87,0,7.71-.27A84.79,84.79,0,0,1,186.49,187.14Z";

function Icon({
  path,
  className,
}: {
  path: string;
  className: string;
}): ReactNode {
  return (
    <svg
      viewBox="0 0 256 256"
      fill="currentColor"
      aria-hidden
      className={clsx(styles.icon, className)}
    >
      <path d={path} />
    </svg>
  );
}

export default function NavbarColorModeToggle({ className }: Props): ReactNode {
  const { colorMode, setColorMode } = useColorMode();
  return (
    // The outer div keeps className alone: the navbar hides it on small screens.
    <div className={className}>
      <div className={styles.toggle}>
        <span aria-hidden className={styles.divider} />
        <button
          type="button"
          className={styles.button}
          onClick={() => setColorMode(colorMode === "dark" ? "light" : "dark")}
          aria-label="Change color mode"
        >
          <Icon path={SUN} className={styles.sun} />
          <Icon path={MOON} className={styles.moon} />
        </button>
      </div>
    </div>
  );
}
