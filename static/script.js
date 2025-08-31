let quizData = [];
let currentIndex = 0;
let score = 0;
let timer;
let timeLeft = 60;
let answeredList = [];

  //問題データの取得
async function fetchQuestions(limit = 100) {
  const res = await fetch(`/api/quiz?limit=${limit}`);
  if (!res.ok) throw new Error("データ取得に失敗しました");
  const json = await res.json();
  return json.items || [];
}

function startGame() {
  // 画面の初期化
  const startBtn = document.querySelector('button.start');
  if (startBtn) startBtn.style.display = 'none';
  document.getElementById('game').style.display = 'block';
  const title = document.getElementById('title');
  if (title) title.style.display = 'none';
  const intro = document.getElementById('intro');
  if (intro) intro.style.display = 'none';
  const note = document.querySelector('.note');
  if (note) note.style.display = 'none';

  // 状態初期化
  currentIndex = 0;
  score = 0;
  timeLeft = 60;
  answeredList = [];

  // 問題取得 → タイマー開始
  fetchQuestions(100).then(items => {
    quizData = items;
    showQuestion();
    clearInterval(timer);
    timer = setInterval(() => {
      timeLeft--;
      const t = document.getElementById('timer');
      if (t) t.innerText = `残り時間: ${timeLeft}秒`;
      if (timeLeft <= 0) {
        clearInterval(timer);
        endGame();
      }
    }, 1000);
  }).catch(err => {
    alert("問題データの取得に失敗しました。再読み込みしてください。");
    console.error(err);
  });
}

function showQuestion() {
  if (currentIndex >= quizData.length) return endGame();
  const q = quizData[currentIndex];
  const qEl = document.getElementById('question');
  if (qEl) qEl.innerText = `「${q.item}」はどのごみ？`;

  const resultDiv = document.getElementById('result');
  if (resultDiv) {
    resultDiv.innerText = '\u00a0';
    resultDiv.classList.remove('correct', 'incorrect');
  }
  document.querySelectorAll('.choices button').forEach(btn => btn.disabled = false);
}

function answer(choice) {
  const current = quizData[currentIndex];
  const correct = current.category;                 // 簡略化5分類の正解
  const full = current.fullCategory || correct;     // 元分類
  const isCorrect = (choice === correct);

  const resultDiv = document.getElementById('result');
  document.querySelectorAll('.choices button').forEach(btn => btn.disabled = true);

  if (isCorrect) {
    score++;
    if (resultDiv) {
      resultDiv.innerText = `✨正解！「${full}」です✨`;
      resultDiv.classList.add('correct');
    }
  } else {
    if (resultDiv) {
      resultDiv.innerText = `❌不正解。正しくは「${full}」です。`;
      resultDiv.classList.add('incorrect');
    }
  }

  answeredList.push({
    item: current.item, correct: correct, full: full, user: choice, result: isCorrect
  });
  currentIndex++;
  setTimeout(showQuestion, 500);
}

function endGame() {
  const total = answeredList.length;
  const accuracy = total ? Math.round((score / total) * 100) : 0;

  let summaryHTML = `
    <h2>ゲーム終了！</h2>
    <p>解答数：${total} 問 ／ 正解数：${score} 問 ／ 正解率：${accuracy}%</p>
    <button class="back-btn" onclick="location.reload()">スタート画面に戻る</button>
    <button class="share-btn" onclick="shareResult(${score}, ${total}, ${accuracy})">結果をSNSでシェア</button>
    <div class="summary">
    <table>
      <tr><th>#</th><th>品名</th><th>あなたの回答</th><th>正解（詳細）</th><th>結果</th></tr>
  `;

  answeredList.forEach((entry, i) => {
    summaryHTML += `
      <tr>
        <td>${i + 1}</td>
        <td>${entry.item}</td>
        <td>${entry.user}</td>
        <td>${entry.full}</td>
        <td>${entry.result ? '〇' : '×'}</td>
      </tr>
    `;
  });

  summaryHTML += '</table></div>';
  const game = document.getElementById('game');
  if (game) game.innerHTML = summaryHTML;
}

function shareResult(score, total, accuracy) {
  const wrongs = answeredList.filter(e => !e.result);
  let detail = wrongs.map(e => `「${e.item}」は${e.full}`).join('、');
  if (detail.length > 100) detail = detail.substring(0, 97) + '…';
  const text = `ごみ分別クイズ\n正解数：${score}/${total}問（正解率：${accuracy}%）\n${detail ? detail + '。\n' : ''}#ごみ分別クイズ`;
  const url = location.href;
  const tweet = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`;
  window.open(tweet, '_blank');}