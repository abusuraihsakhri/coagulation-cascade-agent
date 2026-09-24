(() => {
  "use strict";

  const root = document.documentElement;
  const themeToggle = document.getElementById("theme-toggle");
  const patternTab = document.getElementById("pattern-tab");
  const mixingTab = document.getElementById("mixing-tab");
  const patternPanel = document.getElementById("pattern-panel");
  const mixingPanel = document.getElementById("mixing-panel");
  const resultTitle = document.getElementById("result-title");
  const resultStatus = document.getElementById("result-status");
  const resultDetails = document.getElementById("result-details");
  const resultNote = document.getElementById("result-note");
  const copyButton = document.getElementById("copy-result");

  const savedTheme = localStorage.getItem("coag-theme");
  if (savedTheme === "dark" || savedTheme === "light") {
    root.dataset.theme = savedTheme;
  }

  themeToggle.addEventListener("click", () => {
    const next = root.dataset.theme === "dark" ? "light" : "dark";
    root.dataset.theme = next;
    localStorage.setItem("coag-theme", next);
  });

  function setMode(mode) {
    const pattern = mode === "pattern";
    patternTab.classList.toggle("active", pattern);
    mixingTab.classList.toggle("active", !pattern);
    patternTab.setAttribute("aria-selected", String(pattern));
    mixingTab.setAttribute("aria-selected", String(!pattern));
    patternPanel.classList.toggle("hidden", !pattern);
    mixingPanel.classList.toggle("hidden", pattern);
  }

  patternTab.addEventListener("click", () => setMode("pattern"));
  mixingTab.addEventListener("click", () => setMode("mixing"));

  function numberValue(id, label, optional = false) {
    const raw = document.getElementById(id).value.trim();
    if (optional && raw === "") return null;
    const value = Number(raw);
    if (!Number.isFinite(value) || value <= 0) {
      throw new Error(`${label} must be a finite value greater than 0.`);
    }
    return value;
  }

  function render(title, status, tone, rows, note) {
    resultTitle.textContent = title;
    resultStatus.textContent = status;
    resultStatus.className = `status ${tone}`;
    resultDetails.replaceChildren();

    for (const [term, description] of rows) {
      const wrap = document.createElement("div");
      const dt = document.createElement("dt");
      const dd = document.createElement("dd");
      dt.textContent = term;
      dd.textContent = description;
      wrap.append(dt, dd);
      resultDetails.append(wrap);
    }

    resultNote.textContent = note;
  }

  function renderError(error) {
    render(
      "Check input",
      "Unable to calculate",
      "bad",
      [["Problem", error.message]],
      "Only positive finite numeric values are accepted."
    );
  }

  patternPanel.addEventListener("submit", (event) => {
    event.preventDefault();
    try {
      const pt = numberValue("pt", "PT");
      const aptt = numberValue("aptt", "aPTT");
      const ptUpper = numberValue("pt-upper", "PT upper limit");
      const apttUpper = numberValue("aptt-upper", "aPTT upper limit");

      const ptProlonged = pt > ptUpper;
      const apttProlonged = aptt > apttUpper;
      let pattern;
      let pathway;
      let interpretation;
      let tone = "neutral";

      if (ptProlonged && !apttProlonged) {
        pattern = "PT prolonged, aPTT not prolonged";
        pathway = "Extrinsic-pathway pattern";
        interpretation = "Consider factor VII-related, vitamin K/VKA, hepatic, and assay/pre-analytic causes in context.";
        tone = "warn";
      } else if (!ptProlonged && apttProlonged) {
        pattern = "PT not prolonged, aPTT prolonged";
        pathway = "Intrinsic-pathway pattern";
        interpretation = "Consider intrinsic-factor deficiency, inhibitor/anticoagulant effect, and pre-analytic causes; mixing studies may help when appropriate.";
        tone = "warn";
      } else if (ptProlonged && apttProlonged) {
        pattern = "Both PT and aPTT prolonged";
        pathway = "Common-pathway / multifactor pattern";
        interpretation = "Consider common-pathway or multifactor processes, anticoagulant effects, liver disease, DIC, dilution, and assay/pre-analytic causes.";
        tone = "warn";
      } else {
        pattern = "Neither test exceeds the supplied upper limit";
        pathway = "No prolongation by supplied cutoffs";
        interpretation = "Normal PT/aPTT does not exclude all hemostatic disorders; interpret with clinical context and the complete laboratory profile.";
        tone = "good";
      }

      render(
        "Pathway pattern",
        pattern,
        tone,
        [
          ["PT", `${pt.toFixed(1)} s · upper limit ${ptUpper.toFixed(1)} s`],
          ["aPTT", `${aptt.toFixed(1)} s · upper limit ${apttUpper.toFixed(1)} s`],
          ["Pattern", pathway],
          ["Interpretation", interpretation],
        ],
        "The supplied reference limits are used exactly as entered; no universal laboratory range is assumed."
      );
    } catch (error) {
      renderError(error);
    }
  });

  mixingPanel.addEventListener("submit", (event) => {
    event.preventDefault();
    try {
      const patient = numberValue("mix-patient", "Patient aPTT");
      const immediate = numberValue("mix-immediate", "Immediate mix aPTT");
      const control = numberValue("mix-control", "Normal pooled plasma aPTT");
      const cutoff = numberValue("mix-cutoff", "ICA cutoff");
      const incubated = numberValue("mix-incubated", "Incubated mix aPTT", true);

      const immediateIca = Math.abs(immediate - control) / patient * 100;
      const corrects = immediateIca <= cutoff;
      const rows = [
        ["Immediate ICA", `${immediateIca.toFixed(2)}%`],
        ["Supplied cutoff", `${cutoff.toFixed(2)}%`],
        ["Immediate interpretation", corrects ? "Meets supplied correction cutoff" : "Exceeds supplied correction cutoff"],
      ];

      let status = corrects ? "Correction pattern at supplied cutoff" : "Inhibitor pattern at supplied cutoff";
      let tone = corrects ? "good" : "warn";

      if (incubated !== null) {
        const incubatedIca = Math.abs(incubated - control) / patient * 100;
        rows.push(["Incubated ICA", `${incubatedIca.toFixed(2)}%`]);
        if (corrects && incubatedIca > cutoff) {
          rows.push(["Incubation pattern", "Immediate correction with loss of correction after incubation; a time-dependent inhibitor pattern is possible."]);
          status = "Time-dependent inhibitor pattern possible";
          tone = "warn";
        } else if (corrects && incubatedIca <= cutoff) {
          rows.push(["Incubation pattern", "Correction persists at the supplied cutoff; a factor-deficiency pattern is favored."]);
        } else {
          rows.push(["Incubation pattern", "Immediate non-correction persists; interpret with anticoagulant exposure and confirmatory testing."]);
        }
      }

      render(
        "Mixing-study ICA",
        status,
        tone,
        rows,
        "Use a locally validated assay-specific cutoff. Mixing studies are one part of the diagnostic workup and are affected by reagent sensitivity and anticoagulants."
      );
    } catch (error) {
      renderError(error);
    }
  });

  copyButton.addEventListener("click", async () => {
    const lines = [resultTitle.textContent, resultStatus.textContent];
    resultDetails.querySelectorAll("div").forEach((row) => {
      const term = row.querySelector("dt")?.textContent ?? "";
      const value = row.querySelector("dd")?.textContent ?? "";
      lines.push(`${term}: ${value}`);
    });
    lines.push(resultNote.textContent);

    try {
      await navigator.clipboard.writeText(lines.join("\n"));
      copyButton.textContent = "Copied";
      window.setTimeout(() => { copyButton.textContent = "Copy"; }, 1200);
    } catch {
      copyButton.textContent = "Unavailable";
      window.setTimeout(() => { copyButton.textContent = "Copy"; }, 1200);
    }
  });
})();
