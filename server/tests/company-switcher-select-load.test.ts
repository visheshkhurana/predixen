// The edit-company dialog must open before @radix-ui/react-select loads.
// Awaiting import() first hid a stale-chunk 404: Edit did nothing and the
// rejection was unhandled. The dialog opens immediately (Skeleton fields),
// and a failed import toasts instead of rejecting.
import assert from "assert";
import { readFileSync } from "fs";

const src = readFileSync("client/src/components/CompanySwitcher.tsx", "utf8");

assert.doesNotMatch(
  src,
  /from\s+["']@\/components\/ui\/select["']/,
  "CompanySwitcher must not statically import the select module",
);

const clickStart = src.indexOf("const handleEditClick");
const clickEnd = src.indexOf("const handleDeleteClick");
assert.ok(clickStart !== -1 && clickEnd > clickStart, "handleEditClick must exist");
const click = src.slice(clickStart, clickEnd);

const openAt = click.indexOf("setEditDialogOpen(true)");
const importAt = click.indexOf("import('@/components/ui/select')");
assert.ok(openAt !== -1, "handleEditClick must open the dialog");
assert.ok(importAt !== -1, "handleEditClick must dynamic-import the select module");
assert.ok(
  openAt < importAt,
  "dialog must open before import() so a chunk failure still shows the editor",
);
assert.doesNotMatch(
  click,
  /await\s+import\s*\(/,
  "import() must not be awaited before the dialog opens",
);
assert.match(click, /\.catch\s*\(/, "import() rejection must be caught");
assert.match(
  click,
  /if\s*\(\s*!mod\?\.Select\s*\)/,
  "a vite:preloadError preventDefault resolves import() to undefined; that must still toast",
);
assert.match(
  src,
  /The editor couldn't load\. Refresh the page and try again\./,
  "failed select chunk must toast that the editor couldn't load and to refresh",
);
assert.match(
  src,
  /selectMod \? \([\s\S]*?\) : \(\s*<Skeleton className="h-9 w-full" \/>\s*\)/,
  "select fields must keep the Skeleton while the module is loading",
);

console.log("PASS  edit dialog opens immediately and catches a failed select chunk");
