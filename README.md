# CrosshairLab v0.2 — Windows用カスタム照準オーバーレイ

Windows 10/11（64bit）を想定した、ゲーム画面に独立ウィンドウで照準を重ねる試作品です。Crosshair Xのソースコード・素材は使用していません。

## 最重要：配布方法とPythonの要否

| 人 | Pythonのインストール | 使うもの |
|---|---|---|
| **一般の利用者** | **不要** | Windows上でビルドした `CrosshairLab.exe` をダブルクリック |
| GitHub ActionsでEXEを作る人 | **ローカルPCには不要** | このソースをGitHubリポジトリへ配置し、クラウド上でビルド |
| Windows PCで自分でビルドする開発者 | 必要 | `build_windows_exe.bat` |
| ソースから直接実行する開発者 | 必要 | `run_windows_dev.bat` |

**重要：このZIPはソース一括パックであり、ビルド済みのEXEを含みません。** 現在の開発環境はWindowsではないため、Windows実行ファイルを生成・実機検証できていません。Python不要で使える形にするためのビルド設定は同梱しています。

PyInstallerはPythonインタプリタとPySide6などをEXEに同梱します。**配布したEXEの利用者に別途Pythonの導入を求めません**。一方、EXEの初回ビルドはWindows環境（GitHub Actionsなど）で行う必要があります。

## 1. 新機能

- 横線：**長さ・中心との隙間・太さ**をそれぞれ独立調整
- 縦線：**長さ・中心との隙間・太さ**をそれぞれ独立調整
- 円形照準：表示切替、**横半径・縦半径・線幅・位置オフセット**を調整
- 横半径と縦半径が等しければ真円、異なれば楕円
- 円と縦横線、中央点を任意に組み合わせ可能（円だけの表示にも対応）
- 線の輪郭、色、透明度、モニター選択、画面中心からのオフセット
- 画面上の照準をクリック透過／最前面に表示
- `Ctrl + Alt + X` で表示／非表示を切替
- 右クリック押下中の非表示（Windows全体の右ボタン状態による簡易動作）
- JSONプリセットの保存・読込、および終了時の現在設定保存
- **v0.1 JSONプリセットを自動移行**：以前の共通長さ・太さ・隙間を縦横両方へ引き継ぐ

## 2. GitHub ActionsでWindows用EXEを作る（自分のPCにPython不要）

1. GitHub上で新規リポジトリを作成します。
2. このフォルダの**中身**をリポジトリのルートに登録します。`app.py`、`model.py`、`requirements-build.txt`、`.github/workflows/build-windows.yml` などがそのままルートから参照できる配置です。
3. GitHubの **Actions** → **Build CrosshairLab Windows EXE** → **Run workflow** を実行します。
4. ビルドが成功すると、その実行画面の **Artifacts** に `CrosshairLab-v0.2-Windows-x64` が現れます。
5. Artifactをダウンロードして展開し、**`CrosshairLab.exe` のみを利用者に配布**できます。利用者にPythonは不要です。

公開ダウンロードページを作りたい場合は、リポジトリでバージョンタグ（例 `v0.2.0`）をpushしてください。設定済みのワークフローがGitHub ReleaseへEXEを添付します。手動で公開する前にビルド・Windows実機試験・適用するライセンス条件の確認を行ってください。

## 3. Windowsでローカルにビルドする（開発者向け）

Pythonが入ったWindows PCで `build_windows_exe.bat` をダブルクリックします。生成先は `dist\CrosshairLab.exe` です。

開発時にソースをそのまま動かす場合は `run_windows_dev.bat` を使用します。これらのバッチは**一般利用者向けの起動方法ではありません**。

## 4. EXEを受け取った人の使い方

1. `CrosshairLab.exe` をダブルクリックします。
2. 設定画面の縦軸・横軸・円／楕円セクションでサイズを変更します。画面右のプレビューと照準表示に反映されます。
3. 円だけにするには「横線を表示」「縦線を表示」「中心点を表示」をオフ、「円形照準を表示」をオンにします。
4. 複数モニターの場合、表示モニターを指定します。
5. `Ctrl + Alt + X` で表示を切り替えます。終了は設定画面の×です。

設定は `%APPDATA%\CrosshairLab\current.json` に保存されます。アンインストール時はEXEの削除に加えて、この設定フォルダを任意で削除できます。レジストリへの設定書込み機構は実装していません。

### 付属プリセット

- `presets/green_cross.json` — 標準の十字
- `presets/white_ring.json` — 真円のみ
- `presets/ellipse_teal.json` — 楕円と中心点
- `presets/ring_cross.json` — 十字と円を合成

このファイルを利用したい場合は、プリセットボタンから個別に読み込んでください。EXE単独配布にはプリセットファイルは含まれないため、必要なら別途渡してください。

## 5. 制約と注意

- **排他的フルスクリーンは未対応**。ボーダーレス／ウィンドウ表示を想定しています。ゲームやOSによってオーバーレイが表示されない場合があります。
- アンチチートやゲーム利用規約への適合は保証できません。プレイ前に利用規約・公式運営の方針を確認してください。
- ゲームプロセスへのDLL注入、メモリ改変、パケット解析、マウス自動操作は実装していません。
- WindowsのDPI倍率やマルチモニター構成により表示位置がずれる場合があります。
- Windows向けEXEは**コード署名をしていません**。配布時、SmartScreen等の警告が表示されることがあります。警告を無条件に回避する手順は推奨しません。署名や配布者の検証が別途必要です。
- PyInstallerの `--onefile` 形式は起動時に一時展開するため、初回起動の遅さやセキュリティソフトの反応があり得ます。
- UIとWindowsの最前面・入力透過は**実機未検証**です。配布前に手元のWindowsで確認してください。
- PySide6/Qtなど、同梱する第三者ライブラリのライセンス条件を配布時に確認してください。

## 6. 自動テスト

以下はGUIに依存しない設定モデル／形状のテストです。

```powershell
python -m unittest discover -s tests -v
```

検査対象は、縦横の独立設定、円・楕円の幾何、旧版プリセット移行、JSON保存・読込、入力範囲の検証などです。

## 7. ファイル構成

```text
CrosshairLab_v0.2/
├── app.py                         # Qt画面 + Windows透過ウィンドウ
├── model.py                       # 設定の整合性、縦横・円の形状計算
├── presets/                       # JSONプリセット4種
├── tests/test_model.py            # GUI不要の自動テスト
├── .github/workflows/build-windows.yml  # GitHub Actions Windows EXEビルド
├── requirements.txt               # 実行依存
├── requirements-build.txt         # 開発・ビルド依存
├── build_windows_exe.bat          # 開発者向けローカルEXEビルド
├── run_windows_dev.bat            # 開発者向けソース実行
└── README.md
```
