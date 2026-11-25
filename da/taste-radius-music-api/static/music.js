const form = document.querySelector("#search-form");
const input = document.querySelector("#query");
const status = document.querySelector("#status");
const statusText = document.querySelector("#status-text");
const spinner = document.querySelector(".spinner");
const tracks = document.querySelector("#tracks");
const count = document.querySelector("#result-count");

let activeSearch;

function element(tag, className, text) {
    const node = document.createElement(tag);
    node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
}

function httpsUrl(value) {
    if (typeof value !== "string") return null;
    try {
        const url = new URL(value);
        if (url.protocol === "https:") return url;
    } catch {
        // Missing or invalid links are omitted from the card.
    }
    return null;
}

function duration(milliseconds) {
    if (!Number.isFinite(milliseconds) || milliseconds < 0) return "재생 시간 정보 없음";
    const seconds = Math.floor(milliseconds / 1000);
    return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

function officialLink(url, className) {
    const link = element("a", className);
    link.href = url.href;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    return link;
}

function trackCard(track) {
    const row = element("li", "track");
    const cover = element("div", "cover");
    cover.setAttribute("aria-hidden", "true");
    cover.append(element("span", "", "♫"));

    const info = element("div", "track-info");
    info.append(
        element("h3", "", track.trackName || "곡 제목 정보 없음"),
        element("p", "", track.artistName || "아티스트 정보 없음"),
        element("p", "", `${track.collectionName || "앨범 정보 없음"} · ${duration(track.trackTimeMillis)}`),
    );

    const links = element("div", "track-links");
    const destination = httpsUrl(track.trackViewUrl);
    if (destination && destination.hostname === "open.spotify.com") {
        const listen = officialLink(destination, "listen");
        listen.textContent = "Spotify에서 듣기";
        listen.setAttribute("aria-label", `${track.trackName || "곡"} Spotify에서 듣기 (새 탭)`);
        links.append(listen);

        const artUrl = httpsUrl(track.artworkUrl100);
        if (artUrl) {
            const artwork = element("img", "");
            artwork.alt = "";
            artwork.addEventListener("error", () => artwork.remove(), { once: true });
            artwork.src = artUrl.href;
            cover.append(artwork);
        }
    } else {
        links.append(element("span", "store", "공식 링크 정보 없음"));
    }

    row.append(cover, info, links);
    return row;
}

function showStatus(state, message) {
    status.hidden = false;
    status.dataset.state = state;
    statusText.textContent = message;
    spinner.hidden = state !== "loading";
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const query = input.value.trim();

    activeSearch?.abort();
    activeSearch = undefined;
    tracks.replaceChildren();
    count.hidden = true;

    if (!query) {
        tracks.setAttribute("aria-busy", "false");
        showStatus("error", "곡명이나 아티스트를 입력해 주세요.");
        input.focus();
        return;
    }

    const controller = new AbortController();
    activeSearch = controller;
    tracks.setAttribute("aria-busy", "true");
    showStatus("loading", "음악을 검색하고 있어요.");

    try {
        const params = new URLSearchParams({ q: query });
        const response = await fetch(`/api/music/search?${params}`, { signal: controller.signal });
        const data = await response.json();
        if (activeSearch !== controller) return;

        if (!response.ok) {
            showStatus("error", data.error || "검색 요청을 처리하지 못했습니다. 다시 시도해 주세요.");
            return;
        }
        if (!Array.isArray(data.results)) throw new Error("Invalid search response");
        if (data.results.length === 0) {
            showStatus("empty", data.message || "검색 결과가 없습니다. 다른 검색어를 입력해 보세요.");
            return;
        }

        tracks.append(...data.results.map(trackCard));
        count.textContent = `${data.results.length}곡`;
        count.hidden = false;
        status.hidden = true;
    } catch {
        if (activeSearch === controller) {
            showStatus("error", "검색 결과를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.");
        }
    } finally {
        if (activeSearch === controller) {
            tracks.setAttribute("aria-busy", "false");
            activeSearch = undefined;
        }
    }
});
