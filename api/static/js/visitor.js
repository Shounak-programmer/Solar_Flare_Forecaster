/**
 * visitor.js — Visitor counter with slot-machine odometer animation.
 *
 * How it works:
 *  1. On page load, POST /api/visitor_count/increment to atomically
 *     increment the MongoDB counter and receive the new total.
 *  2. Build a "digit reel" for each digit of the number: a column of
 *     spans (0-9) that slides vertically to the correct digit.
 *  3. Animate with a staggered delay so digits roll like a real odometer.
 */

(function () {
  "use strict";

  /* -- Odometer builder ---------------------------------------------------- */

  function buildOdometer(container) {
    var currentDigits = [];

    function ensureSlots(numDigits) {
      while (currentDigits.length < numDigits) {
        var slot = document.createElement("span");
        slot.className = "odo-digit";

        var inner = document.createElement("span");
        inner.className = "odo-digit-inner";
        for (var i = 0; i <= 9; i++) {
          var row = document.createElement("span");
          row.textContent = String(i);
          inner.appendChild(row);
        }
        slot.appendChild(inner);

        if (container.firstChild) {
          container.insertBefore(slot, container.firstChild);
        } else {
          container.appendChild(slot);
        }
        currentDigits.unshift({ slot: slot, inner: inner });
      }

      while (currentDigits.length > numDigits) {
        var removed = currentDigits.shift();
        container.removeChild(removed.slot);
      }
    }

    function setDigit(inner, d, delay) {
      inner.style.transition = "none";
      void inner.offsetHeight;
      setTimeout(function () {
        inner.style.transition = "transform .55s cubic-bezier(.22,.68,0,1.2)";
        inner.style.transform = "translateY(" + (-1.2 * d) + "em)";
      }, delay);
    }

    function setCount(count) {
      var str = String(Math.max(0, Math.floor(count)));
      var digits = str.split("").map(Number);

      ensureSlots(digits.length);

      digits.forEach(function (d, i) {
        var delay = (digits.length - 1 - i) * 80;
        setDigit(currentDigits[i].inner, d, delay);
      });
    }

    setCount(0);
    return { setCount: setCount };
  }

  /* -- Main ----------------------------------------------------------------- */

  function initVisitorCounter() {
    var container = document.getElementById("visitorOdometer");
    if (!container) return;

    container.innerHTML = "";
    var odo = buildOdometer(container);

    fetch("/api/visitor_count/increment", { method: "POST" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        var count = data.visitor_count;
        if (typeof count === "number" && count >= 0) {
          setTimeout(function () { odo.setCount(count); }, 300);
        }
      })
      .catch(function (err) {
        console.warn("Visitor counter unavailable:", err.message);
        container.textContent = "?";
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initVisitorCounter);
  } else {
    initVisitorCounter();
  }
})();
