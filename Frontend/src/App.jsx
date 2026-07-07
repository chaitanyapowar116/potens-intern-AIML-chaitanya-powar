import { useState } from 'react';

function parseAnswer(rawAnswer) {
  const text = typeof rawAnswer === 'string' ? rawAnswer : String(rawAnswer ?? '');
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);

  const entries = [];
  let currentEntry = { context: '', source: '' };

  const pushCurrentEntry = () => {
    if (!currentEntry.context && !currentEntry.source) {
      return;
    }

    entries.push({ ...currentEntry });
    currentEntry = { context: '', source: '' };
  };

  lines.forEach((line) => {
    if (/^answer\d*:/i.test(line)) {
      pushCurrentEntry();
      currentEntry.context = line.replace(/^answer\d*:\s*/i, '');
    } else if (/^source\d*:/i.test(line)) {
      currentEntry.source = line.replace(/^source\d*:\s*/i, '');
      pushCurrentEntry();
    } else if (!line.startsWith('user_query:')) {
      if (currentEntry.context) {
        currentEntry.context += `\n${line}`;
      } else {
        currentEntry.context = line;
      }
    }
  });

  if (currentEntry.context || currentEntry.source) {
    pushCurrentEntry();
  }

  return {
    entries,
    fallbackContext: entries.length ? '' : text,
  };
}

function formatContradictionResult(result) {
  if (!result) {
    return 'No contradiction result returned.';
  }

  if (typeof result === 'string') {
    try {
      return JSON.stringify(JSON.parse(result), null, 2);
    } catch {
      return result;
    }
  }

  return JSON.stringify(result, null, 2);
}

function App() {
  const [query, setQuery] = useState('');
  const [resultBlocks, setResultBlocks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [contradictionLoading, setContradictionLoading] = useState(false);
  const [error, setError] = useState('');
  const [contradictionError, setContradictionError] = useState('');
  const [contradictionResult, setContradictionResult] = useState('');
  const [lastAnswer, setLastAnswer] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!query.trim()) {
      setError('Please enter a question.');
      return;
    }

    setLoading(true);
    setError('');
    setResultBlocks([]);

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
      const sources = Array.isArray(data.sources) ? data.sources : [];

      setLastAnswer(rawAnswer);

      const blocks = parsed.entries.length
        ? parsed.entries
        : sources.length
          ? sources.map((item) => ({
              context: parsed.fallbackContext || 'No answer returned.',
              source: [item.source, item.page ? `Page ${item.page}` : ''].filter(Boolean).join(' • '),
            }))
          : [{ context: parsed.fallbackContext || 'No answer returned.', source: 'No sources returned.' }];

      setResultBlocks(blocks);
    } catch (err) {
      setError(err.message || 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  };

  const handleContradict = async () => {
    if (!query.trim()) {
      setContradictionError('Please ask a query first.');
      return;
    }

    if (!lastAnswer.trim()) {
      setContradictionError('Please ask a query first to get an answer.');
      return;
    }

    setContradictionLoading(true);
    setContradictionError('');
    setContradictionResult('');

    try {
      const response = await fetch('/contradict', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ contents: [query.trim(), lastAnswer.trim()] }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Unable to compare the texts.');
      }

      setContradictionResult(formatContradictionResult(data.result));
    } catch (err) {
      setContradictionError(err.message || 'Something went wrong.');
    } finally {
      setContradictionLoading(false);
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
          <div className="button-row">
            <button type="submit" disabled={loading}>
              {loading ? 'Thinking...' : 'Ask'}
            </button>
            <button type="button" className="secondary-button" onClick={handleContradict} disabled={contradictionLoading}>
              {contradictionLoading ? 'Checking...' : 'Contradict'}
            </button>
          </div>
        </form>

        {error ? <p className="error">{error}</p> : null}
        {contradictionError ? <p className="error">{contradictionError}</p> : null}

        <div className="result-stack">
          {contradictionResult ? (
            <article className="result-block">
              <div className="result-row">
                <span className="result-label">Contradiction Result</span>
                <pre>{contradictionResult}</pre>
              </div>
            </article>
          ) : (
            <div className="empty-state">Contradiction analysis will appear here.</div>
          )}

          {resultBlocks.length ? (
            resultBlocks.map((item, index) => (
              <article className="result-block" key={`${item.source || 'source'}-${index}`}>
                <div className="result-row">
                  <span className="result-label">Context</span>
                  <p>{item.context || 'No context returned.'}</p>
                </div>
                <div className="result-row">
                  <span className="result-label">Source</span>
                  <p>{item.source || 'No source returned.'}</p>
                </div>
              </article>
            ))
          ) : (
            <div className="empty-state">Your answer will appear here.</div>
          )}
        </div>
      </section>
    </main>
  );
}

export default App;
