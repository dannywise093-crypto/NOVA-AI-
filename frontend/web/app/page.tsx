"use client";

import { FormEvent, useState } from "react";

const suggestions = [
  { icon: "⌘", title: "Build something", detail: "Plan and create a project" },
  { icon: "◎", title: "Explore an idea", detail: "Research a topic deeply" },
  { icon: "↗", title: "Analyze a file", detail: "Understand your documents" },
  { icon: "✳", title: "Solve a problem", detail: "Reason through the hard parts" },
];

export default function HomePage() {
  const [prompt, setPrompt] = useState("");
  const [notice, setNotice] = useState("");

  function submitPrompt(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!prompt.trim()) return;
    setNotice("The workspace UI is ready. Connect the NOVA API to enable live model responses.");
  }

  return (
    <main className="shell">
      <aside className="sidebar">
        <a className="brand" href="#" aria-label="NOVA AI home">
          <span className="brand-mark">N</span>
          <span>NOVA<span className="brand-light"> AI</span></span>
        </a>
        <button className="new-work" onClick={() => { setPrompt(""); setNotice(""); }}>
          <span>＋</span> New workspace
          <kbd>⌘ K</kbd>
        </button>
        <div className="nav-label">WORKSPACE</div>
        <button className="nav-item active"><span>◈</span> Overview</button>
        <button className="nav-item"><span>◷</span> Recent activity</button>
        <button className="nav-item"><span>▤</span> Library</button>
        <div className="nav-label projects-label">YOUR SPACE</div>
        <button className="nav-item"><span>＋</span> New project</button>
        <div className="sidebar-bottom">
          <div className="upgrade-card">
            <div className="upgrade-icon">✧</div>
            <strong>Think beyond limits.</strong>
            <p>Your ideas deserve a powerful workspace.</p>
            <span className="soon">MORE CAPABILITIES COMING</span>
          </div>
          <button className="profile"><span className="avatar">N</span><span><strong>NOVA User</strong><small>Personal workspace</small></span><span className="dots">···</span></button>
        </div>
      </aside>

      <section className="main-panel">
        <header className="topbar">
          <div className="breadcrumb">Workspace <span>/</span> <strong>Overview</strong></div>
          <div className="top-actions"><span className="status-dot" /> <span>Preview</span><button className="icon-button" aria-label="Settings">⚙</button></div>
        </header>

        <div className="content">
          <div className="eyebrow"><span className="sparkle">✳</span> YOUR INTELLIGENCE, AMPLIFIED</div>
          <h1>Make room for<br /><span>what’s possible.</span></h1>
          <p className="intro">One space to explore ideas, solve complex problems, and turn your thinking into something real.</p>

          <form className="composer" onSubmit={submitPrompt}>
            <label className="sr-only" htmlFor="prompt">What would you like to work on?</label>
            <textarea id="prompt" value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Ask NOVA anything, or describe what you want to create..." rows={3} />
            <div className="composer-footer">
              <div className="composer-tools">
                <button type="button" title="Attach files" onClick={() => setNotice("File upload will be enabled when the workspace API is connected.")}>＋ <span>Attach</span></button>
                <button type="button" title="Choose a mode" onClick={() => setNotice("Research, create, and analyze modes are on the roadmap.")}>◈ <span>Modes</span></button>
              </div>
              <button className="send-button" type="submit" disabled={!prompt.trim()}>Start thinking <span>↗</span></button>
            </div>
          </form>
          {notice && <p className="notice" role="status">{notice}</p>}

          <div className="section-heading"><span>START WITH AN IDEA</span><span className="section-line" /></div>
          <div className="suggestions">
            {suggestions.map((item) => (
              <button className="suggestion" key={item.title} onClick={() => { setPrompt(item.title + ": "); setNotice(""); }}>
                <span className="suggestion-icon">{item.icon}</span>
                <strong>{item.title}</strong>
                <span className="suggestion-detail">{item.detail}</span>
                <span className="suggestion-arrow">↗</span>
              </button>
            ))}
          </div>

          <div className="bottom-note"><span className="note-icon">✳</span><p><strong>Built for curiosity. Designed for momentum.</strong><br />NOVA is being built as a complete AI workspace — not just a chat window.</p></div>
        </div>
        <footer><span>NOVA AI <span className="footer-sep">/</span> FOUNDATION PREVIEW</span><span>Intelligence, amplified.</span></footer>
      </section>
    </main>
  );
}  async function runTask(event: FormEvent) {
    event.preventDefault();
    if (!goal.trim()) return;
    setBusy(true); setResult(null); setEvents([]);
    try {
      const response = await fetch(API + "/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
        body: JSON.stringify({ goal })
      });
      if (!response.ok || !response.body) throw new Error("NOVA stream unavailable");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() ?? "";
        for (const chunk of chunks) {
          const line = chunk.split("\n").find(item => item.startsWith("data: "));
          if (!line) continue;
          const data = JSON.parse(line.slice(6));
          if (data.type === "response.final") {
            setResult({
              content: data.content,
              model: data.model,
              provider: data.provider,
              capabilities: [],
              verification: { passed: true, score: 1 },
              events: []
            });
          } else {
            setEvents(current => [...current, data]);
          }
        }
      }
    } catch (error) {
      setEvents([{ type: "error", message: error instanceof Error ? error.message : "Unknown error" }]);
    } finally {
      setBusy(false);
    }
  }
