// PNG export: the visible area, or the whole path at native resolution.

import { EXPORT_MAX_DIM, EXPORT_MAX_PX } from "./config.js";
import { $, cv } from "./dom.js";
import { pathImage } from "./model.js";
import { artworkReady, paint, preloadPath } from "./render.js";
import { LAYOUT, cellOrigin, state } from "./state.js";
import { toast } from "./toast.js";

// a permission prompt can defer the blob's read indefinitely, so the URL lives
// until the next export replaces it
let exportUrl = null;

function download(blob, name) {
  if (!blob) {
    toast("export failed");
    return;
  }
  if (exportUrl) URL.revokeObjectURL(exportUrl);
  exportUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = exportUrl;
  a.download = name;
  a.click();
}

const exportName = (kind) =>
  `oddworld-${state.data.id.toLowerCase()}${state.lvl ? "-" + state.lvl.short : ""}${state.path ? "-P" + state.path.id : ""}-${kind}.png`;

$("exportBtn").onclick = () => {
  const name = exportName("view");
  cv.toBlob((blob) => download(blob, name), "image/png");
};

// A canvas past a browser's limit says nothing about it: drawing into one is
// ignored, or the size asked for is quietly clamped, and a blank canvas encodes
// to a perfectly good multi-megabyte PNG. One pixel painted and read back is
// the answer that holds however the refusal arrives.
function sizedCanvas(w, h) {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  const g = c.width === w && c.height === h ? c.getContext("2d") : null;
  if (g) {
    g.fillStyle = "#fff";
    g.fillRect(0, 0, 1, 1);
    try {
      if (g.getImageData(0, 0, 1, 1).data[3]) return [c, g];
    } catch {
      /* a readback the browser refuses answers neither way */
    }
  }
  c.width = c.height = 0; // a clamped store was still allocated
  return null;
}

const pathBtn = $("exportPathBtn");
const PATH_LABEL = pathBtn.textContent.trim();

pathBtn.onclick = async () => {
  const path = state.path;
  if (!path) return;
  pathBtn.disabled = true;
  pathBtn.textContent = "Rendering…";
  try {
    await preloadPath(path);
    // two frames: the first commits the label, the second paints it before the
    // render takes the thread. A hidden page paints no frames at all, so a timer
    // releases the wait rather than holding the export until the tab is looked at
    await new Promise((r) => {
      requestAnimationFrame(() => requestAnimationFrame(r));
      setTimeout(r, 100);
    });
    // paint draws the path that is standing, into a canvas sized for the one
    // whose artwork was preloaded: both have to still hold, and nothing may
    // come between these and the paint
    if (state.path !== path) {
      toast("export cancelled");
      return;
    }
    if (!artworkReady(path)) {
      toast("export failed: artwork did not load");
      return;
    }
    // read before the encode: at this size the encode is long enough for the
    // place it names to move under it
    const name = exportName("full");
    let im, canvas;
    for (let px = EXPORT_MAX_PX, dim = EXPORT_MAX_DIM; !canvas && dim >= 1024; px /= 4, dim /= 2) {
      im = pathImage(path, LAYOUT, px, dim);
      canvas = sizedCanvas(im.w, im.h);
    }
    if (!canvas) {
      toast("export failed");
      return;
    }
    const [ecv, ectx] = canvas;
    const [ox, oy] = cellOrigin();
    paint(ectx, { x: ox, y: oy, z: im.scale }, im.w, im.h, 1, false);
    if (im.scale < 1) toast(`too large at full size: scaled to ${Math.round(im.scale * 100)}%`);
    const blob = await new Promise((r) => ecv.toBlob(r, "image/png"));
    ecv.width = ecv.height = 0; // the backing store must not wait on the GC
    download(blob, name);
  } finally {
    pathBtn.disabled = false;
    pathBtn.textContent = PATH_LABEL;
  }
};
