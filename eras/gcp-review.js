/* Paris 1878 GCP review desk. Inside the existing Leaflet city page.
 * Select paired locations on two independent maps. Never rewrite the source
 * georeference or declare a historical pixel independently verified.
 */
"use strict";
window.GcpReview = (() => {
  const SOURCE = "data/paris-1878-research-overlay.json";
  const esc = (x) => String(x == null ? "" : x).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

  async function mount(args) {
    const root = args.root;
    if (!root || !root.isConnected || !window.L) return;
    const select = root.querySelector("#gcpSelect");
    const decision = root.querySelector("#gcpDecision");
    const reviewer = root.querySelector("#gcpReviewer");
    const notes = root.querySelector("#gcpNotes");
    const evidence = root.querySelector("#gcpEvidence");
    const proposals = root.querySelector("#gcpProposals");
    const status = root.querySelector("#gcpReviewStatus");
    const exportButton = root.querySelector("#gcpExport");
    const allButton = root.querySelector("#gcpAll");
    const records = new Map();
    const response = await fetch(SOURCE);
    if (!response.ok) {
      status.textContent = "Не удалось загрузить документ опорных точек.";
      return;
    }
    const data = await response.json();
    if (!root.isConnected) return;
    if (data.city_id !== "paris" || data.verification !== "manual_GCP_review_required" ||
        data.gcps.length !== 15 || !data.source_catalogue.startsWith("https://www.loc.gov/")) {
      status.textContent = "Файл исследовательских точек не прошёл проверку.";
      return;
    }

    const originalWidth = data.source_image_width;
    const originalHeight = data.source_image_height;
    const oldAt = (px, py) => args.at(
      px * args.plan.width / originalWidth,
      py * args.plan.height / originalHeight
    );
    const oldFocus = L.circleMarker([0, 0], { radius: 10, color: "#a33d35", weight: 3,
      fillOpacity: 0, interactive: false }).addTo(args.oldMap);
    const newFocus = L.circleMarker([0, 0], { radius: 10, color: "#236b55", weight: 3,
      fillOpacity: 0, interactive: false }).addTo(args.modernMap);
    let oldProposal = null;
    let newProposal = null;
    let currentIndex = 0;
    let current = null;

    select.replaceChildren();
    data.gcps.forEach((g, i) => {
      const option = document.createElement("option");
      option.value = String(i);
      option.textContent = String(i + 1) + ". " + g.name +
        (g.confidence === "low" ? " (низкая уверенность)" : "");
      select.appendChild(option);
    });

    function showProposals() {
      const saved = records.get(currentIndex) || {};
      oldProposal = saved.proposed_pixel || null;
      newProposal = saved.proposed_lonlat || null;
      proposals.textContent =
        "Из исторического плана: " + (oldProposal ? oldProposal.join(", ") : "не выбрано") +
        "; из современной карты: " + (newProposal ? newProposal.join(", ") : "не выбрано") +
        ". Выбор не меняет исходный каталог.";
    }

    function store() {
      if (!current) return;
      const saved = records.get(currentIndex) || {};
      records.set(currentIndex, {
        ...saved,
        requested_decision: decision.value,
        reviewer: reviewer.value.trim(),
        notes: notes.value.trim(),
        evidence_url: evidence.value.trim(),
        proposed_pixel: oldProposal,
        proposed_lonlat: newProposal,
      });
    }

    function focus(index, zoom = true) {
      if (!root.isConnected) return;
      currentIndex = index;
      current = data.gcps[index];
      if (!current) return;
      select.value = String(index);
      const oldPosition = oldAt(current.px, current.py);
      const newPosition = [current.lat, current.lon];
      oldFocus.setLatLng(oldPosition);
      newFocus.setLatLng(newPosition);
      if (zoom) {
        // Same named landmark in each panel, with independent projections.
        const span = 550;
        const bounds = L.latLngBounds(oldAt(current.px - span, current.py - span),
          oldAt(current.px + span, current.py + span));
        args.oldMap.fitBounds(bounds, { padding: [16, 16], maxZoom: args.plan.max_zoom + 2 });
        args.modernMap.setView(newPosition, 17, { animate: false });
      }
      const saved = records.get(index) || {};
      decision.value = saved.requested_decision || "pending";
      reviewer.value = saved.reviewer || "";
      notes.value = saved.notes || "";
      evidence.value = saved.evidence_url || "";
      showProposals();
      status.textContent = current.name + ": остаток модели " +
        Number(current.residual_affine_m).toFixed(1) + " м; точка не подтверждена экспертом.";
    }

    select.addEventListener("change", () => {
      store();
      focus(Number(select.value));
    });
    [decision, notes, evidence, reviewer].forEach(el =>
      el.addEventListener("change", store));

    args.oldMap.on("click", e => {
      if (root.hidden || !root.isConnected || !current) return;
      const px = args.oldMap.project(e.latlng, args.plan.max_zoom);
      oldProposal = [
        Math.round(px.x * originalWidth / args.plan.width * 10) / 10,
        Math.round(px.y * originalHeight / args.plan.height * 10) / 10,
      ];
      store();
      showProposals();
      status.textContent = "Предложен новый пиксель; проверка источника обязательна.";
    });
    args.modernMap.on("click", e => {
      if (root.hidden || !root.isConnected || !current) return;
      newProposal = [Number(e.latlng.lng.toFixed(7)), Number(e.latlng.lat.toFixed(7))];
      store();
      showProposals();
      status.textContent = "Предложены современные координаты; это не экспертное утверждение.";
    });

    allButton.addEventListener("click", () => {
      store();
      args.oldMap.fitBounds(L.latLngBounds(data.gcps.map(p => oldAt(p.px, p.py))),
        { padding: [28, 28] });
      args.modernMap.fitBounds(L.latLngBounds(data.gcps.map(p => [p.lat, p.lon])),
        { padding: [28, 28], maxZoom: 15 });
      status.textContent = "Показаны все 15 исследовательских точек. Их точность не подтверждена.";
    });

    exportButton.addEventListener("click", () => {
      store();
      const items = data.gcps.map((p, i) => {
        const entry = records.get(i) || {};
        const claimed = entry.requested_decision || "pending";
        const evidenceOk = /^https:\/\/[^ ]+$/i.test(entry.evidence_url || "");
        const sufficient = Boolean(entry.reviewer && entry.notes && evidenceOk);
        return {
          index: i + 1, name: p.name, qid: p.qid,
          archival_pixel: [p.px, p.py], modern_lonlat: [p.lon, p.lat],
          old_pick_confidence: p.confidence,
          recorded_residual_m: p.residual_affine_m,
          requested_decision: claimed,
          decision: ["accept", "revise"].includes(claimed) && !sufficient
            ? "insufficient_evidence" : claimed,
          proposed_pixel: entry.proposed_pixel || null,
          proposed_lonlat: entry.proposed_lonlat || null,
          reviewer_claim: entry.reviewer || "",
          evidence_url: entry.evidence_url || "",
          notes: entry.notes || "",
          certified: false,
        };
      });
      const protocol = {
        schema: "city-on-paper/gcp-review-draft/v1",
        city: "Paris", map: "Paris et ses environs : 1878",
        source_url: data.source_catalogue,
        modern_aerial_source: "IGN ORTHOIMAGERY.ORTHOPHOTOS",
        modern_imagery_acquisition_year: null,
        exported_at_utc: new Date().toISOString(),
        review_status: "unverified_draft_requires_independent_signoff",
        coordinates_changed_in_museum: false,
        entries: items,
      };
      const blob = new Blob([JSON.stringify(protocol, null, 2) + "\n"],
        { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "paris-1878-gcp-review-draft.json";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      status.textContent = "Черновой протокол выгружен. Исходные 15 GCP не изменены.";
    });
    focus(0, false);
    return { focus, data };
  }

  return { mount };
})();