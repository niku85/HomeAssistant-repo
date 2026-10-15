/*
 * Chore Reminder card for Home Assistant.
 *
 * Served automatically by the chore_reminder integration, so no manual
 * resource registration is needed.
 *
 *   type: custom:chore-reminder-card
 *   title: Chores            # optional
 *   entities:                # chore sensors (sensor.<chore name>)
 *     - sensor.water_plants
 *     - sensor.change_bed_sheets
 *   confirm: true            # optional, tap the refresh button twice to mark done
 */

const DOMAIN = "chore_reminder";
const CARD_VERSION = "1.1.0";

const STRINGS = {
  en: {
    due_today: "Due today",
    due_tomorrow: "Due tomorrow",
    days_left: (n) => `${n} days left`,
    days_overdue: (n) => (n === 1 ? "1 day overdue" : `${n} days overdue`),
    target: "Target date",
    mark_done: "Mark as done",
    confirm_done: "Tap again to mark as done",
    change_date: "Change due date",
    unavailable: "Entity not available",
    no_entities: "No chores selected",
  },
  de: {
    due_today: "Heute fällig",
    due_tomorrow: "Morgen fällig",
    days_left: (n) => `Noch ${n} Tage`,
    days_overdue: (n) => (n === 1 ? "1 Tag überfällig" : `${n} Tage überfällig`),
    target: "Zieldatum",
    mark_done: "Als erledigt markieren",
    confirm_done: "Zum Bestätigen erneut tippen",
    change_date: "Fälligkeitsdatum ändern",
    unavailable: "Entität nicht verfügbar",
    no_entities: "Keine Aufgaben ausgewählt",
  },
};

const isChoreSensor = (hass, entityId) =>
  entityId.startsWith("sensor.") &&
  (hass.entities?.[entityId]?.platform === DOMAIN ||
    hass.states[entityId]?.attributes?.next_due !== undefined);

const escapeHtml = (value) =>
  String(value).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[c]);

class ChoreReminderCard extends HTMLElement {
  static getStubConfig(hass) {
    const chores = Object.keys(hass.states).filter((id) => isChoreSensor(hass, id));
    return { entities: chores.slice(0, 3) };
  }

  static getConfigForm() {
    return {
      schema: [
        { name: "title", selector: { text: {} } },
        { name: "confirm", selector: { boolean: {} } },
        {
          name: "entities",
          required: true,
          selector: {
            entity: {
              multiple: true,
              filter: { integration: DOMAIN, domain: "sensor" },
            },
          },
        },
      ],
      computeLabel: (schema) =>
        ({
          title: "Title",
          entities: "Chores",
          confirm: "Ask for a second tap before marking done",
        })[schema.name] ?? schema.name,
    };
  }

  setConfig(config) {
    const entities = config.entities ?? (config.entity ? [config.entity] : []);
    if (!Array.isArray(entities)) {
      throw new Error("'entities' must be a list of chore sensors.");
    }
    this._config = {
      confirm: true,
      ...config,
      entities: entities.map((e) => (typeof e === "string" ? e : e.entity)),
    };
    this._busy = new Set();
    this._armed = undefined;
    this._lastRendered = undefined;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 1 + 2 * (this._config?.entities.length ?? 1);
  }

  getGridOptions() {
    return { columns: 6, min_columns: 3 };
  }

  get _t() {
    const lang = (this._hass?.locale?.language ?? this._hass?.language ?? "en").split("-")[0];
    return STRINGS[lang] ?? STRINGS.en;
  }

  _formatDate(isoDate) {
    const [y, m, d] = isoDate.split("-").map(Number);
    try {
      return new Intl.DateTimeFormat(this._hass.locale?.language ?? undefined, {
        weekday: "short",
        year: "numeric",
        month: "short",
        day: "numeric",
      }).format(new Date(y, m - 1, d));
    } catch (_err) {
      return isoDate;
    }
  }

  _daysText(daysUntil, daysOverdue) {
    const t = this._t;
    if (daysOverdue > 0) return t.days_overdue(daysOverdue);
    if (daysUntil === 0) return t.due_today;
    if (daysUntil === 1) return t.due_tomorrow;
    return t.days_left(daysUntil);
  }

  _rerender() {
    this._lastRendered = undefined;
    this._render();
  }

  // With `confirm` on, the first tap only arms the button; a second tap within
  // a few seconds marks the chore done. Protects against accidental taps.
  _onDoneTap(entityId) {
    if (!this._config.confirm || this._armed === entityId) {
      this._disarm();
      this._markDone(entityId);
      return;
    }
    this._disarm();
    this._armed = entityId;
    this._armTimer = setTimeout(() => this._disarm(), 4000);
    this._rerender();
  }

  _disarm() {
    clearTimeout(this._armTimer);
    if (this._armed !== undefined) {
      this._armed = undefined;
      this._rerender();
    }
  }

  // The chore's editable "Next due date" entity sits on the same device.
  _nextDueEntity(entityId) {
    const deviceId = this._hass.entities?.[entityId]?.device_id;
    if (!deviceId) return undefined;
    return Object.values(this._hass.entities).find(
      (e) => e.device_id === deviceId && e.platform === DOMAIN && e.entity_id.startsWith("date.")
    )?.entity_id;
  }

  async _markDone(entityId) {
    if (this._busy.has(entityId)) return;
    this._busy.add(entityId);
    this._lastRendered = undefined;
    this._render();
    try {
      await this._hass.callService(DOMAIN, "mark_done", {}, { entity_id: entityId });
    } catch (err) {
      // Surface the error the same way HA's own cards do.
      this.dispatchEvent(
        new CustomEvent("hass-notification", {
          detail: { message: `Chore Reminder: ${err.message ?? err}` },
          bubbles: true,
          composed: true,
        })
      );
    } finally {
      this._busy.delete(entityId);
      this._lastRendered = undefined;
      this._render();
    }
  }

  _openMoreInfo(entityId) {
    this.dispatchEvent(
      new CustomEvent("hass-more-info", { detail: { entityId }, bubbles: true, composed: true })
    );
  }

  _renderChore(entityId) {
    const t = this._t;
    const stateObj = this._hass.states[entityId];
    if (!stateObj || stateObj.state === "unavailable" || stateObj.state === "unknown") {
      return `<div class="chore missing">${escapeHtml(entityId)}: ${t.unavailable}</div>`;
    }

    const a = stateObj.attributes;
    const daysUntil = Number(stateObj.state);
    const overdue = a.overdue === true || daysUntil < 0;
    const daysOverdue = Number(a.days_overdue ?? Math.max(0, -daysUntil));
    const progress = Math.min(100, Math.max(0, Number(a.progress ?? 0)));
    const name = a.chore_name ?? a.friendly_name ?? entityId;
    const busy = this._busy.has(entityId);
    const armed = this._armed === entityId;
    const buttonLabel = armed ? t.confirm_done : t.mark_done;
    const icon = busy ? "mdi:loading" : armed ? "mdi:check" : "mdi:refresh";

    return `
      <div class="chore ${overdue ? "overdue" : ""}" data-entity="${escapeHtml(entityId)}">
        <div class="header">
          <div class="name" data-action="more-info">${escapeHtml(name)}</div>
          ${armed ? `<span class="confirm-hint">${t.confirm_done}</span>` : ""}
          <button class="done ${armed ? "armed" : ""}" data-action="done" title="${buttonLabel}"
                  aria-label="${buttonLabel}" ${busy ? "disabled" : ""}>
            <ha-icon icon="${icon}" class="${busy ? "spin" : ""}"></ha-icon>
          </button>
        </div>
        <div class="info">
          <div class="days">
            ${overdue ? '<ha-icon class="alert" icon="mdi:alert-circle"></ha-icon>' : ""}
            <span>${escapeHtml(this._daysText(daysUntil, daysOverdue))}</span>
          </div>
          <button class="target" data-action="edit-date" title="${t.change_date}"
                  aria-label="${t.target}: ${escapeHtml(this._formatDate(a.next_due))}. ${t.change_date}">
            <ha-icon icon="mdi:calendar-edit"></ha-icon>
            <span>${escapeHtml(this._formatDate(a.next_due))}</span>
          </button>
        </div>
        <div class="bar" role="progressbar" aria-valuemin="0" aria-valuemax="100"
             aria-valuenow="${progress}">
          <div class="fill" style="width: ${overdue ? 100 : progress}%"></div>
        </div>
      </div>`;
  }

  _render() {
    if (!this._config || !this._hass) return;

    // Only re-render when one of our entities changed.
    const signature = JSON.stringify([
      this._hass.locale?.language,
      ...this._config.entities.map((id) => {
        const s = this._hass.states[id];
        return s ? [s.state, s.attributes.next_due, s.attributes.progress, s.attributes.chore_name] : null;
      }),
    ]);
    if (signature === this._lastRendered) return;
    this._lastRendered = signature;

    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.addEventListener("click", (ev) => {
        const actionEl = ev.target.closest("[data-action]");
        const choreEl = ev.target.closest("[data-entity]");
        if (!actionEl || !choreEl) return;
        const entityId = choreEl.dataset.entity;
        const action = actionEl.dataset.action;
        if (action === "done") this._onDoneTap(entityId);
        if (action === "more-info") this._openMoreInfo(entityId);
        if (action === "edit-date") this._openMoreInfo(this._nextDueEntity(entityId) ?? entityId);
      });
    }

    const title = this._config.title
      ? `<h1 class="card-header">${escapeHtml(this._config.title)}</h1>`
      : "";
    const body = this._config.entities.length
      ? this._config.entities.map((id) => this._renderChore(id)).join("")
      : `<div class="chore missing">${this._t.no_entities}</div>`;

    this.shadowRoot.innerHTML = `
      <style>${ChoreReminderCard.styles}</style>
      <ha-card>${title}<div class="content">${body}</div></ha-card>`;
  }

  static get styles() {
    return `
      :host {
        --chore-ok-color: var(--success-color, #43a047);
        --chore-overdue-color: var(--error-color, #db4437);
      }
      ha-icon {
        display: inline-flex; flex: none;
        width: var(--mdc-icon-size, 24px); height: var(--mdc-icon-size, 24px);
      }
      .card-header { padding-bottom: 0; }
      .content { padding: 16px; display: flex; flex-direction: column; gap: 20px; }
      .chore { display: flex; flex-direction: column; gap: 8px; }
      .header { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
      .name {
        font-size: 1.2em; font-weight: 500; cursor: pointer;
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
      }
      .done {
        flex: none; display: inline-flex; align-items: center; justify-content: center;
        width: 40px; height: 40px; border-radius: 50%; border: none; cursor: pointer;
        background: var(--secondary-background-color, rgba(127,127,127,.15));
        color: var(--primary-text-color);
        transition: background .2s, color .2s;
      }
      .done:hover { background: var(--chore-ok-color); color: #fff; }
      .done:disabled { cursor: default; opacity: .6; }
      .overdue .done { background: var(--chore-overdue-color); color: #fff; }
      .done.armed, .overdue .done.armed { background: var(--chore-ok-color); color: #fff; }
      .confirm-hint {
        margin-left: auto; font-size: .85em; color: var(--chore-ok-color);
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
      }
      .target {
        border: none; background: none; padding: 2px 4px; margin: -2px -4px;
        font: inherit; color: inherit; cursor: pointer; border-radius: 6px;
      }
      .target:hover { background: var(--secondary-background-color, rgba(127,127,127,.15)); }
      .info {
        display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
        gap: 4px 12px; color: var(--secondary-text-color);
      }
      .days, .target { display: inline-flex; align-items: center; gap: 4px; }
      .days { font-size: 1.3em; font-weight: 500; color: var(--primary-text-color); }
      .overdue .days { color: var(--chore-overdue-color); }
      .alert { color: var(--chore-overdue-color); --mdc-icon-size: 22px; }
      .target ha-icon { --mdc-icon-size: 18px; }
      .bar {
        height: 10px; border-radius: 5px; overflow: hidden;
        background: var(--divider-color, rgba(127,127,127,.25));
      }
      .fill {
        height: 100%; border-radius: 5px; background: var(--chore-ok-color);
        transition: width .4s ease, background .4s ease;
      }
      .overdue .fill { background: var(--chore-overdue-color); }
      .missing { color: var(--warning-color, #ffa600); }
      .spin { animation: spin 1s linear infinite; }
      @keyframes spin { to { transform: rotate(360deg); } }
    `;
  }
}

const registerCard = () => {
  if (customElements.get("chore-reminder-card")) return;
  customElements.define("chore-reminder-card", ChoreReminderCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "chore-reminder-card",
    name: "Chore Reminder",
    description: "Countdown, target date and progress bar for your chores.",
    preview: true,
    documentationURL: "https://github.com/niku85/homeassistant-repo",
  });
  console.info(`%c CHORE-REMINDER-CARD %c v${CARD_VERSION} `,
    "color:#fff;background:#43a047;font-weight:700", "color:#43a047");
};

// The integration injects this script into the page, so it can run before the
// Home Assistant app has started. The app replaces window.customElements with
// its own registry on startup, and anything defined before that is invisible
// to it ("Configuration error", card missing from the picker). So wait until
// the app has defined its root element; give up waiting after 30 seconds.
const appReady = () =>
  customElements.get("home-assistant") || customElements.get("hc-main");

if (appReady()) {
  registerCard();
} else {
  const started = Date.now();
  const timer = setInterval(() => {
    if (appReady() || Date.now() - started > 30000) {
      clearInterval(timer);
      registerCard();
    }
  }, 50);
}
