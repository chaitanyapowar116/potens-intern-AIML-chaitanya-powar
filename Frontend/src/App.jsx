import { useState } from 'react';

function parseAnswer(rawAnswer) {
  const text = typeof rawAnswer === 'string' ? rawAnswer : String(rawAnswer ?? '');
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);

  const output = [];
  const sources = [];

  lines.forEach((line) => {
    if (/^answer\d*:/i.test(line)) {
      output.push(line.replace(/^answer\d*:\s*/i, ''));
    } else if (/^source\d*:/i.test(line)) {
      sources.push(line.replace(/^source\d*:\s*/i, ''));
    } else if (!line.startsWith('user_query:')) {
      output.push(line);
    }
  });

  return {
    output: output.join('\n'),
    sources: sources.join('\n'),
  };
}

function App() {
  const [query, setQuery] = useState('');
  const [output, setOutput] = useState('');
  const [sources, setSources] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!query.trim()) {
      setError('Please enter a question.');
      return;
    }

    setLoading(true);
    setError('');
    setOutput('');
    setSources('');

    try {
      const response = await fetch('/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Unable to get a response.');
      }

      const rawAnswer = data.answer?.content || data.answer || '';
      const parsed = parseAnswer(rawAnswer);

      setOutput(parsed.output || 'No answer returned.');
      setSources(parsed.sources || 'No sources returned.');
    } catch (err) {
      setError(err.message || 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="app-shell">
      <section className="card">
        <p className="eyebrow">Simple Chatbot</p>
        <h1>Ask your documents</h1>
        <p className="subtext">
          Enter a question and the app will query the backend for an answer and the related sources.
        </p>

        <form onSubmit={handleSubmit} className="chat-form">
          <textarea
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Type your question here..."
            rows={4}
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Thinking...' : 'Ask'}
          </button>
        </form>

        {error ? <p className="error">{error}</p> : null}

        <div className="result-grid">
          <article className="result-panel">
            <h2>Output</h2>
            <pre>{output || 'Your answer will appear here.'}</pre>
          </article>

          <article className="result-panel">
            <h2>Source</h2>
            <pre>{sources || 'Sources will appear here.'}</pre>
          </article>
        </div>
      </section>
    </main>
  );
}

export default App;
