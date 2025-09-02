let quizData = [];
let currentIndex = 0;
let score = 0;
let timer = null;
let timeLeft = 60;
let answeredList = [];

// 問題データをサーバから取得
async function fetchQuestions(limit = 100) {
  const res = await fetch(`/api/quiz?limit=${limit}`);
  if (!res.ok) throw new Error("データ取得に失敗しました");
  const json = await res.json();
  return json.items || [];
}

// ボタン表示名 → 内部で使う分類名（表記ゆれ対応）
function normalizeChoice(choice) {
  if (choice === 'リサイクル') return '資源ごみ';
  return choice;
}

// タイマー表示を更新
function updateTimer() {
  const t = document.getElementById('timer');
  if (t) t.innerText = `残り時間: ${timeLeft}秒`;
}

// ゲーム開始
async function startGame() {
  // スタート画面の非表示
  const startBtn = document.querySelector('button.start');
  if (startBtn) startBtn.style.display = 'none';
  const title = document.getElementById('title');
  if (title) title.style.display = 'none';
  const intro = document.getElementById('intro');
  if (intro) intro.style.display = 'none';
  const note = document.querySelector('.note');
  if (note) note.style.display = 'none';

  // ゲーム画面の表示
  const gameDiv = document.getElementById('game');
  if (gameDiv) gameDiv.style.display = 'block';

  // 状態初期化
  currentIndex = 0;
  score = 0;
  timeLeft = 60;
  answeredList = [];
  updateTimer();

  try {
    quizData = await fetchQuestions(100);
  } catch (e) {
    alert("問題データの取得に失敗しました。再読み込みしてください。");
    console.error(e);
    return;
  }

  showQuestion();

  // 既存タイマーを止めてから新たに開始
  if (timer) clearInterval(timer);
  timer = setInterval(() => {
    timeLeft--;
    updateTimer();
    if (timeLeft <= 0) {
      clearInterval(timer);
      endGame();
    }
  }, 1000);
}

// 問題を表示
function showQuestion() {
  if (currentIndex >= quizData.length) {
    endGame();
    return;
  }

  const q = quizData[currentIndex];
  const qEl = document.getElementById('question');
  if (qEl) qEl.innerText = `「${q.item}」はどのごみ？`;

  const resultDiv = document.getElementById('result');
  if (resultDiv) {
    resultDiv.innerText = '\u00a0';
    resultDiv.classList.remove('correct', 'incorrect');
  }

  document.querySelectorAll('.choices button').forEach(btn => {
    btn.disabled = false;
  });
}

// 回答処理
function answer(choice) {
  const current = quizData[currentIndex];
  const correct = current.category;                 // 簡略化5分類の正解
  const full = current.fullCategory || correct;     // 元の分類
  const userChoice = normalizeChoice(choice);
  const isCorrect = (userChoice === correct);

  const resultDiv = document.getElementById('result');
  document.querySelectorAll('.choices button').forEach(btn => {
    btn.disabled = true;
  });

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
    item: current.item,
    correct: correct,
    full: full,
    user: userChoice,
    result: isCorrect
  });

  currentIndex++;
  setTimeout(showQuestion, 500);
}

// 結果表示
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

// 共有（Twitter）
function shareResult(score, total, accuracy) {
  const wrongs = answeredList.filter(e => !e.result);
  let detail = wrongs.map(e => `「${e.item}」は${e.full}`).join('、');
  if (detail.length > 100) detail = detail.substring(0, 97) + '…';
  const text = `平泉町ごみ分別クイズ\n正解数：${score}/${total}問（正解率：${accuracy}%）\n${detail ? detail + '。\n' : ''}#ごみ分別クイズ`;
  const url = location.href;
  const tweet = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`;
  window.open(tweet, '_blank');
}