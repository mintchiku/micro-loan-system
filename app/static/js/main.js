// Small helpers only. Live EMI preview on the Apply page (same formula as app/services/emi.py).

function calculateEmi(principal, annualRate, months) {
  const r = annualRate / 12 / 100; // monthly rate as a fraction
  if (r === 0) return principal / months;
  const growth = Math.pow(1 + r, months);
  return (principal * r * growth) / (growth - 1);
}

function maxAffordableAmount(maxEmi, annualRate, months) {
  const r = annualRate / 12 / 100; // EMI formula solved for the principal
  if (r === 0) return Math.floor(maxEmi * months);
  const growth = Math.pow(1 + r, months);
  return Math.floor((maxEmi * (growth - 1)) / (r * growth));
}

function formatInr(value) {
  // en-IN gives Indian grouping: 1,00,000.00
  return "₹" + value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Busy state: the moment a form is submitted, its button shows a spinner and ignores second clicks
// (instant feedback, and no double payments). The button is NOT disabled, so its value still posts.
document.addEventListener("submit", function (event) {
  if (event.defaultPrevented) return; // a confirm() dialog was cancelled
  const form = event.target;
  const button = event.submitter || form.querySelector('button[type="submit"]');
  if (!button || button.classList.contains("is-busy")) return;
  button.classList.add("is-busy");
  button.setAttribute("aria-busy", "true");
  button.insertAdjacentHTML("afterbegin", '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span>');
});

// A page restored from the browser's back/forward cache must not stay in the busy state
window.addEventListener("pageshow", function () {
  document.querySelectorAll(".is-busy").forEach(function (button) {
    button.classList.remove("is-busy");
    button.removeAttribute("aria-busy");
    const spinner = button.querySelector(".spinner-border");
    if (spinner) spinner.remove();
  });
});

document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("apply-form");
  if (!form) return; // not on the Apply page

  const rate = parseFloat(form.dataset.rate);
  const income = parseFloat(form.dataset.income);
  const maxEmi = (income * parseFloat(form.dataset.maxPct)) / 100;
  const minAmount = parseFloat(form.dataset.minAmount);
  const maxAmount = parseFloat(form.dataset.maxAmount);
  const minTenure = parseInt(form.dataset.minTenure, 10);
  const maxTenure = parseInt(form.dataset.maxTenure, 10);
  const amountInput = document.getElementById("amount");
  const tenureInput = document.getElementById("tenure_months");
  const message = document.getElementById("preview-message");

  function show(id, text) {
    document.getElementById(id).textContent = text;
  }

  function updatePreview() {
    const amount = parseFloat(amountInput.value);
    const months = parseInt(tenureInput.value, 10);
    show("preview-limit", formatInr(maxEmi));
    if (!(amount > 0) || !(months > 0)) {
      ["preview-emi", "preview-total", "preview-interest"].forEach((id) => show(id, "-"));
      message.className = "small mt-2 text-muted";
      message.textContent = "Enter an amount and tenure to see your EMI.";
      return;
    }

    const emi = Math.round(calculateEmi(amount, rate, months) * 100) / 100; // round to paise
    const total = Math.round(emi * months * 100) / 100;
    show("preview-emi", formatInr(emi));
    show("preview-total", formatInr(total));
    show("preview-interest", formatInr(total - amount));

    if (amount < minAmount || amount > maxAmount) {
      message.className = "small mt-2 text-danger";
      message.textContent = "Amount must be between " + formatInr(minAmount) + " and " + formatInr(maxAmount) + ".";
    } else if (months < minTenure || months > maxTenure) {
      message.className = "small mt-2 text-danger";
      message.textContent = "Tenure must be between " + minTenure + " and " + maxTenure + " months.";
    } else if (emi > maxEmi) {
      const best = Math.min(maxAffordableAmount(maxEmi, rate, months), maxAmount);
      message.className = "small mt-2 text-danger";
      message.textContent = "EMI is above your limit. For " + months + " months you can borrow at most " + formatInr(best) + ".";
    } else {
      message.className = "small mt-2 text-success";
      message.textContent = "This EMI is within your limit.";
    }
  }

  amountInput.addEventListener("input", updatePreview);
  tenureInput.addEventListener("input", updatePreview);
  updatePreview(); // show values kept after a form error
});
