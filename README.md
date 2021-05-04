## 概要

状態を管理しない関数のみで、音楽波形データをシンプルに生成できないだろうか？
外部ライブラリを使うことなく、指定時間におけるサンプル値を返す関数、`sample(t)`のみで音楽を表現する。

## 再現した曲と生成物

[ファルコム音楽フリー宣言](https://www.falcom.co.jp/music-use) を活用させていただき、今回対象曲として、

```
翼をもった少年 / ミュージックフロム イースIII ワンダラーズフロムイース / Copyright © Nihon Falcom Corporation
```

を利用させてもらった。たいへんありがたい。


リアルタイム生成を試せるページは [こちら](https://htsnul.github.io/function_music/)。（Chrome、Safariで動作確認した）
wavファイル生成してmp3に変換したものは [こちら](https://htsnul.github.io/function_music/output.mp3)。
コード（JavaScriptを主とする約600行のhtmlファイル）は[こちら](https://github.com/htsnul/function_music/blob/main/index.html) 。


## 準備

以下のhtmlを雛形として開始する。

```js
<!DOCTYPE html>
<meta charset="utf-8">
<div><button class="start" autofocus>Start</button></div>
<script>
  const sampleRate = 44100;
  function sample(t) {
    return 0.25 * Math.sin(2 * Math.PI * 440 * t);
  }
  document.querySelector(".start").onclick = (e) => {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    const audioCtx = new AudioContext();
    const seconds = 3;
    const audioBuffer = audioCtx.createBuffer(1, seconds * sampleRate, sampleRate);
    const data = audioBuffer.getChannelData(0);
    for (let i = 0; i < seconds * sampleRate; ++i) {
      const t = i / sampleRate;
      data[i] = sample(t);
    }
    const audioBufferSourceNode = audioCtx.createBufferSource();
    audioBufferSourceNode.buffer = audioBuffer;
    audioBufferSourceNode.connect(audioCtx.destination);
    audioBufferSourceNode.start(audioCtx.currentTime + 0.5);
  }
</script>
```

「Start」ボタンを押すと、`sample`を3秒間分呼び出しして、波形データを生成し、それを Web Audio を利用して再生する。

当然ながら Web Audio は波形データを再生することだけに使っていて、Web Audio のシンセサイザ機能は利用していない。
本質的な部分は、

```js
  function sample(t) {
    return 0.2 * Math.sin(2 * Math.PI * 440 * t);
  }
```

と、時間から1サンプルデータを返している部分のみだ。

これで440Hzのラの音が3秒間鳴ることが確認できるはずだ。
今回の音楽生成は基本的にこの延長で実現することになる。

これで、今後実装していく`sample(t)`を確認するための環境の準備が整った。

## 簡単なFM変調

進める上で、sin関数そのままの音ではちょっと気持ち悪いし聞き取りづらい。
この段階で簡単でもよいのでFM音源的なFM変調を掛ける。

```js
    return 0.2 * Math.sin(angVel * t);
```

となっていた部分を、

```js
    return 0.05 * Math.sin(
      angVel * t +
      4 * Math.sin(1 * angVel * t)
    );
```

としよう。
FM変調は基本的に、上記のように`sin`の中にもう1つ`sin`を足してしまえばよい。
中の`sin`の角速度は、基本的には、基準となる角速度の整数倍にする。

倍音が出て音が少し聞き取りやすくなったと思う。
各種値を変更することで音色の変化を確認できる。

FM音源については [FMシンセのあたらしいトリセツ](https://www.amazon.co.jp/dp/B07BBFVX7J) がお勧めだ。

## 音色関数

音を任意の時間・音階で複数鳴らせるようにするために、音色部分を関数化する。

音階を周波数で指定するのは難しいため、まずはMIDI準拠のノートナンバーから角周波数を計算できるようにしておく。
69が440Hzのラで、1増減するごとに半音ずつ増減する。

```js
  function angularVelFromNoteNumber(nn) {
    return 2 * Math.PI * 440 * 2 ** ((nn - 69) / 12);
  }
```

時間・音の長さ・ノートナンバーを受け取って、1つの音として鳴らせるようにする。

```js
  function toneSimple(t, duration, nn) {
    if (t < 0 || duration < t) return 0;
    const angVel = angularVelFromNoteNumber(nn); 
    return 0.2 * Math.sin(angVel * t);
  }
```

範囲外だった場合は、すぐに0を返すようにすることで、特定区間の間だけ鳴るようにしている。
この関数自体は、時間0から音が鳴り始める前提にしておき、0以外の時間に音を鳴らしたいときは、渡す前の時間を減算する。

上記を使って、1秒ずつドレミを鳴らす`sample(t)`は、以下になる。

```js
  function sample(t) {
    let d = 0;
    d += toneSimple(t - 0, 1, 72);
    d += toneSimple(t - 1, 1, 74);
    d += toneSimple(t - 2, 1, 76);
    return d;
  }
```

これで任意の時間・音階で音色を鳴らせるようになった。

## エンベロープ

ここまでの実装だと音の開始と終了がプツプツ切れてしまうし、鳴っている間の音が平坦だ。
そこで、ノートオン・ノートオフに対して音量がどのように変化するかを表すエンベロープを導入する。

Wikipediaの [ADSR](https://ja.wikipedia.org/wiki/ADSR) の項目が参考になる。

今回は状態管理なしで実現する必要があるため、`t`を受け取り音量を返す関数が必要になる。

各傾斜をclamp関数で表現すると良さそうに思われたため、clamp関数を用意しておく。

```js
  function clamp(val, minVal, maxVal) {
    return Math.max(minVal, Math.min(val, maxVal));
  }
```

各時間がゼロの場合、ゼロ除算で分岐が必要になり複雑になることと、速度にも影響があることから、
エンベロープ関数は必要な引数に応じて分離することにした。

```js
  function envelopeR(t, rt) {
    return Number(0 <= t) - clamp(t / rt, 0, 1);
  }
  function envelopeAR(t, at, rt) {
    return clamp(t / at, 0, 1) - clamp((t - at) / rt, 0, 1);
  }
  function envelopeASR(t, duration, at, rt) {
    return Math.max(0, (
      clamp(t / at, 0, Math.min(duration / at, 1)) -
      clamp((t - duration) / rt, 0, 1)
    ));
  }
  function envelopeDR(t, duration, dt, rt) {
    return Math.max(0, (
      Number(0 <= t) -
      clamp(t / dt, 0, duration / dt) -
      Math.max(0, (t - duration) / rt)
    ));
  }
  function envelopeADR(t, duration, at, dt, rt) {
    return Math.max(0, (
      clamp(t / at, 0, Math.min(duration / at, 1)) -
      clamp((t - at) / dt, 0, Math.max(0, (duration - at) / dt)) -
      Math.max(0, (t - duration) / rt)
    ));
  }
```

アタックタイム途中でノートオフ（durationを超える）する場合は、リリースはその時点での音量から下がるよう考慮が必要になるため、`envelopeASR`・`envelopeADR` ではそのあたりを考慮している。
`envelopeADSR` は、今回使わなかったので用意しなかったが、普通に実装できるはず。

これを音色関数に組み込んでみる。

```js
  function toneSimple(t, duration, nn) {
    const e = envelopeADR(t, duration, 0.02, 1.5, 0.1);
    if (e == 0) return 0;
    const angVel = angularVelFromNoteNumber(nn); 
    return 0.05 * e * Math.sin(
      angVel * t +
      4 * Math.sin(1 * angVel * t)
    );
  }
```

エンベロープによりだいぶ音が自然になった。

## テンポと拍

ここまで、時間は秒で指定していたが、実際の音楽の入力を考えると、拍を使いたい。
拍を使うために必要なのは、拍と秒の変換だ。
拍と秒の変換はテンポに依存する。

```js
  const tempo = 120;
  const spb = 60 / tempo;
```

`spb`は seconds per beat、1拍あたりの秒数だ。
使用頻度が高いので定数名も短くしている。

これを使えば、これまで秒数で指定してた音の関数への指定を拍指定にできる。

```js
  function sample(t) {
    let d = 0;
    d += toneSimple(t - 0 * spb, 1 * spb, 72);
    d += toneSimple(t - 1 * spb, 1 * spb, 74);
    d += toneSimple(t - 2 * spb, 1 * spb, 76);
    return d;
  }
```

四分音符指定でドレミが鳴らせるようになった。

途中でテンポが変化する場合は、ちょっと複雑になりそうだ。この記事では踏み込んでいない。

## MML的な入力

ここまでの記述を見ると、ドレミを鳴らすだけでも記述量がだいぶ多いことが気になってくる。
これではさすがに規模の大きい曲を入力は厳しく感じられる。

そこで、最低限の実装で、ある程度MML的な記述ができるようにしていく。

まずは、ノートナンバーを文字列で指定できるようにするために、文字列からノートナンバーに変換する関数を作る。

```js
  function noteNumberFromString(str) {
    const octaveOffset = 12 * (str.codePointAt(0) - "4".codePointAt(0));
    const scaleOffset = { "c": -9, "d": -7, "e": -5, "f": -4, "g":-2, "a": 0, "b": 2 }[str[1]];
    const sharpFlatOffset = (str[2] === "+" ? 1 : 0) + (str[2] === "-" ? -1 : 0);
    return 69 + octaveOffset + scaleOffset + sharpFlatOffset;
  }
```

これで、`4c` とか `5d+` とかのMML的な指定で音階を指定できるようになる。

また、入力自体もコンパクトにしたい。複数の音を同時に配列で記載できるようにする。

```js
  function notes(t, toneFunc, params) {
    let d = 0;
    let nt = 0;
    for (let p of params) {
      if (t < nt) break;
      [noteStr, gateBeat, stepBeat] = p;
      if (stepBeat === undefined) stepBeat = gateBeat;
      d += toneFunc(t - nt, gateBeat * spb, noteNumberFromString(noteStr));
      nt += stepBeat * spb;
    }
    return d;
  }
```

色々仕様を考えた結果、
音階名・ゲートタイム（拍）・ステップタイム（拍）の3パラメータの配列を渡すのが、
実装の簡潔さ・表現幅・入力の簡潔さ、のバランスが良さそうに感じた。

ゲートタイムとステップタイムが同じ場合には、ステップタイムは省略できる（ほとんどの場合そうなる）。
また、和音を入力したい場合には、和音の最後以外のステップタイムで0を指定すればよい。

昔「ST/GT方式」と呼ばれる入力があったらしいが、それに近い部分があるかもしれない。

多くのMMLでは、長さを全音符の分数で指定するようになっているが、分数での指定は意図的に避けた。
理由は、ゲートタイム（拍）とステップタイム（拍）を同じ尺度で考えれるようにしたいのと、
長さの足し算をしやすくするためだ。
海外でMMLと似た ABC notation というものがあるが、これも分数指定ではない。

`notes` 関数を利用することで、ドレミは以下のように入力できるようになった。

```js
  function sample(t) {
    let d = 0;
    d += notes(t, toneSimple, [
      ["5c", 1], ["5d", 1], ["5e", 1]
    ]);
    return d;
  }
```

これで最低限の実装でコンパクトさを備えた音符の入力手段が手に入った。

対象曲中から具体例を出すと、後半の前半の主旋律は以下のように記述している。

```js
    d += notes(t, toneLead2, [
      ["4e-", 2, 2.5], ["4e-", 0.5], ["4f", 0.5], ["4g", 0.5, 0.5 + 1],
      ["4g", 1], ["4f", 0.5], ["4e-", 0.5 + 0.5],
      ["4f", 0.5 + 3, 0.5 + 3.5], ["4d", 0.5 + 3 + 0.5],
      ["4e-", 0.5 + 2.5], ["4f", 0.5], ["4g", 0.5],
      ["4e-", 0.5 + 2.5], ["4f", 0.5], ["4g", 0.5],
      ["4f+", 0.5 + 2], ["4g", 1.5], ["4a", 0.5, 0.5 + 1],
      ["4f+", 1], ["4g", 0.5], ["4a", 0.5 + 0.5],
    ]);
```

## 繰り返し

入力をしていると繰り返しをしたくなる場面が出てくる。
この際、普通に `for` でループを回すこともできるのだが、
せっかく関数を使っているので、`t` の剰余を使おう。

```js
  function repeat(t, duration, count) {
    if (t < 0) return t;
    if (count * duration <= t) return t - (count - 1) * duration;
    return t % duration;
  }
```

この関数は、`t` を受け取るが、0から `count * duration` の間を、`duration` で割ってその剰余にしてしまう。
こうすると、結果的に `t` が `duration` の間を `count` 回巻き戻って繰り返す値に変換でき、結果として繰り返しになる。

`for` を使うよりもこちらのほうが圧倒的に速度が速くなる。
実際本記事の対象曲でも、`repeat` を使わないとリアルタイム生成は間に合わなくなることがあった。

```js
  function sample(t) {
    let d = 0;
    d += notes(repeat(t, 2 * spb, 4), toneSimple, [
      ["5c", 0.5], ["5d", 0.5], ["5e", 0.5], ["5f", 0.5]
    ]);
    return d;
  }
```

とすることで、ほぼ速度劣化なしで8分音符のドレミファを4回繰り返すことができる。

例えば、対象曲の後半のピコピコ鳴っている部分は以下のように `repeat` で済ませている。

```js
    d += notes(repeat(t, 1 * spb, 24), toneSquareSynth, [
      ["5b-", 0.25], ["5g", 0.25], ["5a", 0.25], ["5g", 0.25]
    ]);
```

## ノイズ

最初、シンバル音をFM変調で音色を作ろうとしたが、
オペレータをかなり増やしてもなかなか綺麗な音にならない。

そこで、ノイズを使う方法を検討した。
`t` から一意に返さなければならないため、単純に `Math.random()` を使うわけにはいかない。
単純なノイズだけでは問題ないかもしれないが、後述するフィルタに適用する場合、入力が一意である必要があるため、ノイズの結果が時間に対して一意であることは必須になる。

シンプルなノイズ関数としては [線形合同法](https://ja.wikipedia.org/wiki/%E7%B7%9A%E5%BD%A2%E5%90%88%E5%90%8C%E6%B3%95) が良さそうで、
そのパラメータは MINSTD と呼ばれている値が良さそうでそれを使おう。

サンプルのインデックスを受け取り、31bitの値を返す。

```js
  function noise31b(n) {
    if (n <= 0) return 1;
    return (48271 * noise31b(n - 1)) % (2 ** 31 - 1);
  });
```

とてもシンプルだが、再帰が使われている点が問題だ。
サンプルのインデックスが大きいと再帰が深くなりすぎてスタックオーバーフローが起きてしまう。
また、そうでなくても時間が掛かりすぎる。

そこで、渡した関数に対して、0から必要部分までをメモ化し、それを利用して値を返す機能を追加した関数を返す関数を作成する。

```js
  const memoiseFrom0 = (f) => {
    const memo = [];
    return (n) => {
      if (n < 0) return f(n);
      for (let i = memo.length; i <= n; ++i) memo[i] = f(i);
      return memo[n];
    }
  };
```

これを使って先ほどの `noise31b` 関数を以下のように変更する。

```js
  const noise31b = memoiseFrom0((n) => {
    if (n <= 0) return 1;
    return (48271 * noise31b(n - 1)) % (2 ** 31 - 1);
  });
```

これで、`noise31b` 関数は、スタックオーバーフローを起こさないし、速度も速くなった。

`noise31b` は31bit値なので、そのままでは使いづらい、他と同じように `-1` ～ `1` の値を返す `noise` 関数を作る。

```js
  function noise(n) { return noise31b(n) / (2 ** 30) - 1; }
```

また、この項での確認のためこのノイズ関数を使った音色関数を作る。

```js
  function toneNoise(t, duration, nn) {
    if (t < 0 || duration <= t) return 0;
    return 0.1 * noise(Math.round(t * sampleRate));
  }
```

時間からサンプルのインデックスに変換している点に注意。

これを使って、

```js
  function sample(t) {
    return toneNoise(t, 1 * spb, 60);
  }
```

とすることでホワイトノイズが鳴らせることが確認できた。
とはいえ、このままではまだシンバルには遠い。次の項目ではこれにフィルタを掛けてシンバルに近づける。

## フィルタ

シンバルの音をそれらしくするには、特定の周波数付近のみに偏ったノイズにしなければならない。
そこで、前項のノイズに対してバンドパスフィルタを掛けられるようにしていく。

バンドパス等の各種フィルタ実装には、[Cookbook formulae for audio equalizer biquad filter coefficients](http://shepazu.github.io/Audio-EQ-Cookbook/audio-eq-cookbook.html) という有名な文章があり、簡単かつ感覚的に使うことができる。

```js
  function biquadFilter(n, a, b, input, output) {
    return (
      b[0] / a[0] * input(n) +
      b[1] / a[0] * input(n - 1) +
      b[2] / a[0] * input(n - 2) +
      -a[1] / a[0] * output(n - 1) +
      -a[2] / a[0] * output(n - 2)
    );
  }
  const bandpassFilteredNoise = memoiseFrom0((n) {
    const freq = 8000;
    const q = 0.5;
    if (n < 0) return 0;
    const omega = 2 * Math.PI * freq / sampleRate;
    const alpha = Math.sin(omega) * q;
    const a = [1 + alpha, -2 * Math.cos(omega), 1 - alpha];
    const b = [alpha, 0, -alpha];
    return biquadFilter(n, a, b, noise, bandpassFilteredNoise);
  });
```

上記の例では、ノイズに対して、8000Hz近辺でバンドパスフィルタを掛けたノイズを取得できる関数を作っている。
`q` の値は、バンドパスフィルタの幅を指定することができる。小さいほど幅が狭くなる。

入力と出力でそれぞれ2サンプルまで過去の値が必要になっている。
こちらもノイズ関数と同じように、再帰が大きくなりすぎる問題があるため、`memoiseFrom0` を適用している。

また、実際には、`freq` と `q` が異なる様々なバンドパスフィルタありノイズ関数を作りたいため、
バンドパスフィルタありノイズ関数を生成する関数を作る。

```js
  function makeBandpassFilteredNoiseFunc(freq, q) {
    const func = memoiseFrom0((n) => {
      if (n < 0) return 0;
      const omega = 2 * Math.PI * freq / sampleRate;
      const alpha = Math.sin(omega) * q;
      const a = [1 + alpha, -2 * Math.cos(omega), 1 - alpha];
      const b = [alpha, 0, -alpha];
      return biquadFilter(n, a, b, noise, func);
    });
    return func;
  }
```

これを利用して、シンバル音色関数を作る。

```js
  const cymbalNoise = makeBandpassFilteredNoiseFunc(4000, 0.2);
  function toneCymbal(t, duration, nn) {
    const e = envelopeAR(t, 0.05, 2);
    if (e == 0) return 0;
    const d = 0.1 * cymbalNoise(Math.round(t * sampleRate));
    return d * (e ** 4);
  }
```

これを鳴らす。

```js
  function sample(t) {
    return toneCymbal(t, 1 * spb, 60);
  }
```

ここまで、それらしいシンバルの音が出せるようになった。

## 様々な音色

ここからは今回の対象曲を再現する中で作った音色を解説する。
基本的にはFM音源的なFM変調を使ったものが多い。

```js
  function toneLead1(t, duration, nn) {
    const e = envelopeDR(t, duration, 3, 0.1);
    if (e == 0) return 0;
    const e1 = envelopeR(t, 1);
    const angVel = angularVelFromNoteNumber(nn); 
    return 0.04 * e * Math.sin(
      angVel * t +
      16.0 * e1 * Math.sin(3 * angVel * t)
    );
  }
```

↑前半で使われているリードシンセ。
少し独特の倍音を感じたので3倍音で変調してみた。原曲がそうなのかは分からない。
この後の音もそうだが、変調を `envelopeR` で減衰させることでFM音源らしさが出る。

```js
  function toneLead2(t, duration, nn) {
    const e = envelopeADR(t, duration, 0.02, 3, 0.1);
    if (e == 0) return 0;
    const e1 = 0.2 + 0.8 * envelopeR(t, 1);
    const angVel = angularVelFromNoteNumber(nn); 
    return 0.05 * e * Math.sin(
      angVel * t +
      15.0 * e1 * Math.sin(1 * angVel * t)
    );
  }
```

↑後半で使われているリードシンセ。
1倍音変調のシンプルな構成。出始めに滑らかさを感じるためアタックタイムも指定している。
このあたりもあえてFM音源らしさを強調した簡素な構成にした。

```js
  function toneSawSynth(t, duration, nn) {
    const e = envelopeADR(t, duration, 0.01, 3, 0.1);
    if (e == 0) return 0;
    const e1 = envelopeR(t, 1);
    const n = 3;
    let d = 0;
    const angVelBase = angularVelFromNoteNumber(nn);
    for (i = 0; i < n; ++i) {
      const angVel = angVelBase + 2 * (-1 * 3 + i) * 2 * Math.PI;
      d += 0.05 / n * Math.sin(
        angVel * t +
        3 * e1 * Math.sin(
          angVel * t +
          3 * e1 * Math.sin(
            angVel * t
          )
        )
      )
    }
    return e * d;
  }
```

↑和音を主に担当するノコギリ波シンセ。
1倍変調を2個直列にしてノコギリ波に近づけている。
さらに、この構成を周波数を微妙にずらしたものを3セット重ねることで厚みを出している。
9オペレータ使っているので、当時のFM音源では不可能な構成で、少し豪華な音になっている。
そういう音も入れてみたかったのでそうした。
また、原曲ではSSGが使われているところも、この音が合いそうに思ったところはこの音にしている。

```js
  function toneSquareSynth(t, duration, nn) {
    const e = envelopeDR(t, duration, 0.2, 0.1);
    if (e == 0) return 0;
    const angVel = angularVelFromNoteNumber(nn); 
    return 0.02 * e * Math.sin(
      angVel * t +
      1.2 * Math.sin(
        2 * angVel * t +
        1.2 * Math.sin(4 * angVel * t)
      )
    );
  }
```

↑後半、16分音符でピコピコ鳴っている矩形波シンセ。
2倍変調、4倍変調と直列にして矩形波に近づけている。
このあたりはセオリー通り。

```js
  function toneBass(t, duration, nn) {
    const e = envelopeDR(t, duration, 3, 0.01);
    if (e == 0) return 0;
    const e1 = envelopeR(t, 0.8);
    const angVel = angularVelFromNoteNumber(nn);
    return 0.04 * e * Math.sin(
      angVel * t +
      15.0 * e1 * Math.sin(angVel * t)
    );
  }
```

↑ベース。
これもよくあるFM音源的な音。これも `envelopeR` を使い、時間変化で変調を大きく減衰させるとそれらしくなる。

```js
  const cymbalNoise = makeBandpassFilteredNoiseFunc(4000, 0.2);
  function toneCymbal(t, duration, nn) {
    const e = envelopeAR(t, 0.05, 2);
    if (e == 0) return 0;
    const d = 0.1 * cymbalNoise(Math.round(t * sampleRate));
    return d * (e ** 4);
  }
```

↑シンバル。
前述のノイズ項で詳しく説明している。
エンベロープを4乗しているのは、時間経過に対してゆっくり減衰するようにするため。

```js
  const hihatNoise = makeBandpassFilteredNoiseFunc(5000, 0.15);
  function toneHihat(t, duration, nn) {
    const e = envelopeADR(t, duration, 0.0005, 0.3, 0.05);
    const d = 0.1 * hihatNoise(Math.round(t * sampleRate));
    return d * e;
  }
```

↑ハイハット。
シンバルとほぼ同じだが、周波数高め・周波数幅狭めでより鋭い音にしている。
また、オープン、クローズは `duration` で使い分けできるようにしている。

```js
  function toneBassDrum(t, duration, nn) {
    const e = envelopeR(t, 0.4);
    if (e == 0) return 0;
    const d = 0.14 * Math.sin(
      50 * t * 2 * Math.PI * (1 + 3 * (Math.max(0, 1 - (t / 0.4)) ** 2)) +
      0.5 * Math.sin(40 * t * 2 * Math.PI)
    );
    return d * (e ** 2);
  }
```

↑バスドラム。
バスドラムは、周波数を高い→低いに短時間で変化させるとそれらしくなることが知られている。
なので、周波数自体を4→1倍に短時間変化させるようにしている。
また、その変化を滑らかにしたくて2乗している。

```js
  const snareDrumNoise = makeBandpassFilteredNoiseFunc(3000, 0.25);
  function toneSnareDrum(t, duration, nn) {
    const e = envelopeR(t, 0.2);
    if (e == 0) return 0;
    let d = 0;
    d += 0.12 * Math.sin(
      (100 + 10 * (nn - 60)) * t * 2 * Math.PI * (1 + 2 * (Math.max(0, 1 - (t / 0.2)) ** 2)) +
      0.02 * Math.sin(40 * t * 2 * Math.PI)
    );
    d += 0.1 * snareDrumNoise(Math.round(t * sampleRate));
    return d * (e ** 2);
  }
```

↑スネアドラム。
スネアドラムは、ノイズ成分と太鼓成分の2つに分けられる。
なので、バスドラムの周波数を少し高くしたものに、ノイズを追加すればそれらしくなる。
また、対象曲中で、タムが使われているが、今回の実装ではスネアドラムで兼用している。
そのため、引数のノートナンバーで音の高さが変わるようにしている。

## 規模の大きさへの対応

規模が大きくなってくると、さすがに `sample(t)` のみに全ての音符を並べることは厳しくなってくる。
そこで、曲をパートごとに分解する。

```js
  function sample(t) {
    return (
      samplePart0(t) +
      samplePart1(t - 4 * spb) +
      samplePart2(t - (4 + 32) * spb) +
      samplePart3(t - (4 + 32 + 32) * spb) +
      samplePart4(t - (4 + 32 + 32 + 32) * spb)
    );
  }
```

各パートでは、それぞれのパートが時間0から始まったとみなして実装すればよい。
また、処理速度が遅くなるのを防ぐため、各パートの実装では、それぞれ時間外だった場合には早期リターンしておくとよい。
ただし、シンコペーションでの先行やエンベロープのリリース部分のはみ出しに応じて、少しマージンを取っておく必要がある。

```js
  function samplePart3(t) {
    if (t < -0.5 * spb || (32 + 1) * spb <= t) return 0;
    // ...
  }
```

冒頭で紹介した Web Audio での再生確認方法では、
曲が長くなってくると開始まで待たされて確認に支障が出てくる。
そこで、1秒ごとに分割して、完成した部分から再生可能にする。

```js
  document.querySelector(".start").onclick = async (e) => {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    const audioCtx = new AudioContext();
    const audioCtxBaseTime = audioCtx.currentTime
    for (let i = 0; i < 60; ++i) {
      const audioBuffer = audioCtx.createBuffer(1, sampleRate, sampleRate);
      const data = audioBuffer.getChannelData(0);
      for (let j = 0; j < sampleRate; ++j) {
        const t = i + j / sampleRate;
        data[j] = sample(t);
        //data[j] = sample(t + (4 + 32 + 32 - 2) * spb);
      }
      const audioBufferSourceNode = audioCtx.createBufferSource();
      audioBufferSourceNode.buffer = audioBuffer;
      audioBufferSourceNode.connect(audioCtx.destination);
      audioBufferSourceNode.start(audioCtxBaseTime + i + 3);
      document.body.innerHTML = i;
      await new Promise((resolve) => setTimeout(() => resolve(), 1));
    }
  }
```

また、曲を途中から確認したい場合には、コメント部分のように `t` をオフセットしてやるとよい。

## WAVファイル出力

最終的な成果物を録音しようとしたが、意外にも良い方法がすぐに見つけれなかったため、WAVファイルで出力できるようにした。

```html
<div><button class="create-download-link">Create Download Link</button></div>
```

```js
  document.querySelector(".create-download-link").onclick = () => {
    const samplesLen = 50 * sampleRate;
    const bytesPerSample = 2;
    const buffer = new ArrayBuffer(44 + samplesLen * bytesPerSample);
    const view = new DataView(buffer);
    [..."RIFF"].forEach((c, i) => view.setUint8(i, c.charCodeAt(0)));
    view.setUint32(4, 32 + samplesLen * bytesPerSample, true);
    [..."WAVE"].forEach((c, i) => view.setUint8(8 + i, c.charCodeAt(0)));
    [..."fmt "].forEach((c, i) => view.setUint8(12 + i, c.charCodeAt(0)));
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * bytesPerSample, true);
    view.setUint16(32, bytesPerSample, true);
    view.setUint16(34, 8 * bytesPerSample, true);
    [..."data"].forEach((c, i) => view.setUint8(36 + i, c.charCodeAt(0)));
    view.setUint32(40, samplesLen * bytesPerSample, true);
    for (let i = 0; i < samplesLen; i++) {
      const t = i / sampleRate;
      const s = sample(t);
      view.setInt16(44 + 2 * i, 0x7fff * s, true);
    }
    const blob = new Blob([view], { type: "audio/wav" });
    const elm = document.createElement("a");
    elm.href = URL.createObjectURL(blob);
    elm.download = "output.wav";
    elm.innerHTML = elm.download;
    document.body.appendChild(elm);
  };
```

## まとめ

本記事では、`sample(t)` のみの実装で音楽を再現する試みを行った。
コードを見てもらえると、仕組みと呼べる部分は少なく、音色と譜面の記述が大部分を占めていることが分かると思う。
この試みで、大掛かりな仕組みを作ることなくシンプルに関数のみで対象曲を表現することで音楽波形データを生成できることが実証できたと思う。

