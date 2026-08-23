// PNG export of the current view.

import { $, cv } from "./dom.js";
import { state } from "./state.js";
import { toast } from "./toast.js";

// a permission prompt can defer the blob's read indefinitely, so the URL lives
// until the next export replaces it
let exportUrl = null;

function download(blob) {
  if (!blob) {
    toast("export failed");
    return;
  }
  if (exportUrl) URL.revokeObjectURL(exportUrl);
  exportUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = exportUrl;
  a.download = `oddworld-${state.data.id.toLowerCase()}${state.lvl ? "-" + state.lvl.short : ""}${state.path ? "-P" + state.path.id : ""}.png`;
  a.click();
}

$("exportBtn").onclick = () => cv.toBlob(download, "image/png");
