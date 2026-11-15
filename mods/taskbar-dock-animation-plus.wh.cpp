// ==WindhawkMod==
// @id                taskbar-dock-animation-plus
// @name              Taskbar Dock Animation Plus
// @name:zh-CN        任务栏 Dock 动画增强版
// @name:ja-JP        タスクバー Dock アニメーション Plus
// @name:ko-KR        작업 표시줄 Dock 애니메이션 Plus
// @name:pt-BR        Animação Dock da Barra de Tarefas Plus
// @name:it-IT        Animazione Dock della Barra delle applicazioni Plus
// @description         Dock-style taskbar magnification with per-app animation modes, scale limits, and independent Widgets control
// @description:uk-UA   Збільшення значків панелі завдань у стилі Dock з режимами та масштабом для кожної програми й окремим керуванням віджетами
// @description:zh-CN   Dock 风格任务栏放大动画，支持按应用选择动画模式、设置放大倍率及单独控制小组件
// @description:ja-JP   Dock 風のタスクバー拡大アニメーション。アプリごとのモードと拡大率、ウィジェットを個別に設定できます
// @description:ko-KR   Dock 스타일 작업 표시줄 확대 애니메이션. 앱별 모드와 확대 비율, 위젯 애니메이션을 개별 설정합니다
// @description:pt-BR   Ampliação da barra de tarefas no estilo Dock, com modos e limites de escala por aplicativo e controle separado de Widgets
// @description:it-IT   Ingrandimento della barra delle applicazioni in stile Dock, con modalità e limiti per app e controllo separato dei widget
// @version           2.1.0
// @author            incconutwo, PDSB001
// @github            https://github.com/incconutwo
// @twitter           https://x.com/tnemoroccan
// @homepage          https://incconutwo.com
// @include           explorer.exe
// @architecture      x86-64
// @compilerOptions -lole32 -loleaut32 -lruntimeobject -lshcore -lwindowsapp -luser32
// ==/WindhawkMod==

/*
MIT License

Copyright (c) Ph0en1x-dev (original work)
Copyright (c) incconutwo (Plus adaptations)
Copyright (c) 2026 PDSB001 (modifications)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
associated documentation files (the "Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the
following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial
portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO
EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
USE OR OTHER DEALINGS IN THE SOFTWARE.
*/

// ==WindhawkModReadme==
/*
# Taskbar Dock Animation Plus

**Co-authors / 共同作者：[incconutwo](https://github.com/incconutwo) · [PDSB001](https://github.com/PDSB001)**

Bring macOS-style Dock magnification to the Windows 11 taskbar. Plus builds on the original Taskbar Dock Animation, with four-edge placement handling, multi-monitor improvements, smooth breathing transitions, and per-app control over how each button animates.

为 Windows 11 任务栏添加 macOS Dock 风格放大动画，支持四边布局、多显示器、平滑呼吸效果，以及按应用设置动画模式和倍率。

**Requires the Windows 11 XAML taskbar. / 需要 Windows 11 的 XAML 任务栏。**

![Taskbar Dock Animation Plus in action](https://raw.githubusercontent.com/pdsb001/windhawk-mods/db6cceac37ce85b8282828915e32ac16cf60e871/assets/taskbar-dock-animation-plus/previews/wave.gif)

## ![Sparkles](https://raw.githubusercontent.com/incconutwo/windhawk-mods/main/assets/sparkles.svg) Features / 功能

- **Dock wave or single-icon zoom:** animate neighboring buttons together, or enlarge only the hovered button.
- **Per-app rules:** choose Wave, Single icon, or Off for each application, with an optional maximum scale. Fixed buttons divide the wave into groups; available space is shared with priority for buttons near the pointer.
- **Four taskbar positions:** bottom, top, left, and right animation directions, with automatic detection and a manual position selector.
- **Multi-monitor handling:** animation state and visual cleanup are managed on each taskbar UI thread.
- **Smooth breathing:** the idle bounce fades in and out. Adjust the curve, radius, spacing, smoothing, and transition duration, or turn breathing off.
- **Widgets and system buttons:** control Widgets separately, exclude Start, or animate app buttons only. Input method, volume, and other system tray icons stay at their normal size.
- **Live settings:** changes take effect without restarting Explorer. Windows Composition applies the animation and skips unchanged visual writes.

可选择波浪联动或仅放大悬停图标，并为不同应用单独指定模式与倍率。固定按钮将波浪划分为独立区段，空间不足时优先保留鼠标附近的放大效果。小组件可单独关闭动画，托盘图标始终排除；设置保存后即时生效。

## Per-app rules / 按应用配置

Run `Get-StartApps` in PowerShell and copy the complete AppUserModelID into a rule. Matching uses the application ID, rather than the window title or executable filename. Custom shortcuts and browser profiles can expose different IDs.

在 PowerShell 中运行 `Get-StartApps`，将完整 AppUserModelID 填入规则。规则按应用 ID 匹配；窗口标题和程序文件名不参与匹配，自定义快捷方式或浏览器配置文件可能使用不同的 ID。

| Setting / 设置 | Behavior / 效果 |
| --- | --- |
| Wave / 波浪 | Joins its wave group / 参与所在区段的波浪动画 |
| Single icon / 仅放大悬停图标 | Zooms independently without shifting neighbors / 单独放大，相邻按钮不跟随位移 |
| Off / 关闭动画 | Keeps its normal size and position / 保持原大小和位置 |
| Maximum scale: 0 / 最大倍率：0 | Inherits the global maximum / 继承全局倍率 |
| Maximum scale: 101–220 / 最大倍率：101–220 | Sets an app-specific maximum percentage / 设置该应用的最大放大百分比 |

Per-app rules override the global mode. Up to 256 rules are read; the last rule for a duplicate ID wins, and empty IDs are ignored. Unmatched applications use the global mode and scale. The maximum is a cap: available space can limit wave magnification.

应用规则优先于全局模式。最多读取 256 条，相同 ID 以最后一条为准，空 ID 忽略。未匹配的应用使用全局设置。倍率是上限，波浪放大还受可用空间限制。

## Taskbar positions / 任务栏位置

If automatic detection gives the wrong direction, choose the actual edge in **Taskbar position**. A manual choice applies to all taskbars and controls animation only; it does not move the Windows taskbar. Use Automatic when monitors have different placements and detection works correctly.

自动识别方向不对时，在“任务栏位置”选择实际的底部、顶部、左侧或右侧。手动选择对所有任务栏生效，只控制动画，不会移动 Windows 任务栏。各显示器位置不同时，可在识别正常的情况下使用自动模式。

![Bottom, top, left, and right taskbar previews](https://raw.githubusercontent.com/PDSB001/windhawk-mods/db6cceac37ce85b8282828915e32ac16cf60e871/assets/taskbar-dock-animation-plus/previews/four-positions.gif?preview=3)

Four separate excerpts from the same desktop recording; vertical views are shown at 50% size. / 四边为同一段实录中不同时间的片段，纵向预览缩小至一半展示。

## Appearance and taskbar sizes / 动画外观与任务栏大小

Start at **130%** maximum scale, then tune the **radius** and spacing for your layout. The global **Enlarge only the hovered icon** switch selects single-icon behavior for applications without an overriding rule. Enable **Taskbar Labels Compatibility** if your taskbar shows window titles.

建议从 **130%** 最大倍率开始，再按布局调节半径和间距。“仅放大悬停图标”决定没有应用规则时的全局模式；任务栏显示窗口标题时，可启用“任务栏标签兼容模式”。

![Default and small taskbar sizes](https://raw.githubusercontent.com/PDSB001/windhawk-mods/db6cceac37ce85b8282828915e32ac16cf60e871/assets/taskbar-dock-animation-plus/previews/taskbar-sizes.gif?preview=3)

Both rows retain the source pixel scale. / 默认与小号两行保留原录像的像素比例。

## ![Triangle Alert](https://raw.githubusercontent.com/incconutwo/windhawk-mods/main/assets/triangle-alert.svg) Compatibility and known issues / 兼容性与已知问题

- **Clipping:** content-aware positioning and reserved indicator space reduce early clipping. Icons that are physically larger than the available taskbar area can still be clipped.
- **Scaling mods:** with **Taskbar height and icon size** or similar mods, start at **130% or lower** and check the result. Adjusting the radius can help suit your layout.
- **Image quality:** enlarged icons may appear slightly blurry.
- **Interaction regions:** Composition changes the drawn position; native clicks, hover highlights, and previews can differ near a shifted icon's edge.
- **StartAllBack:** unsupported. Supporting its taskbar would require a different implementation.
- **Other taskbar mods:** placement, sizing, and styling combinations need validation on the target setup.

边界校正和横条预留空间可以改善提前裁切，但图标大于任务栏可用区域时仍可能裁切，放大后也可能模糊。配合任务栏尺寸模组时建议从 130% 或更低开始，并调节半径。移位图标边缘的原生点击、高亮和预览区域可能与绘制位置有偏差。不支持 StartAllBack，其他任务栏模组组合需分别验证。

## Testing / 测试记录

Desktop testing and the previews use **Windows 11 Pro Insider Preview 26H2, OS build 26340.9882**. The submitter confirmed per-app modes, rule priority, Widgets control, app-only filtering, and the 160% icon/indicator correction on this setup. Strict x64 compilation and automated layout, geometry, and indicator checks also passed. These results do not cover every Windows build or taskbar-mod combination.

本机实测环境为上述系统版本，已确认按应用模式、规则优先级、小组件控制、仅应用过滤及 160% 图标和横条修正。严格 x64 编译与自动布局、坐标和横条检查通过；不同系统版本和模组组合需分别验证。

## ![Globe](https://raw.githubusercontent.com/incconutwo/windhawk-mods/main/assets/globe.svg) Authors and support / 作者与支持

| Co-author / 共同作者 | Profile / 主页 |
| --- | --- |
| incconutwo | [github.com/incconutwo](https://github.com/incconutwo) |
| PDSB001 | [github.com/PDSB001](https://github.com/PDSB001) |

### incconutwo's links / incconutwo 的链接

- **Personal Website & Projects:** [incconutwo.com](https://incconutwo.com)
- **Support My Work:** [Ko-fi](https://ko-fi.com/incconutwo)
- **GitHub Profile:** [github.com/incconutwo](https://github.com/incconutwo)
- **X (Twitter):** [@tnemoroccan](https://x.com/tnemoroccan)

For device-specific issues, including Dell / Alienware setups, open an issue or contact the authors. Animation ideas and curve suggestions are welcome in the mod topic or by direct message.

如遇设备相关问题（包括 Dell / Alienware），可提交问题或联系维护者。也欢迎在模组讨论中提出动画和曲线建议。

## ![Heart](https://raw.githubusercontent.com/incconutwo/windhawk-mods/main/assets/heart.svg) Credits / 致谢

- [Ph0en1x-dev](https://github.com/Ph0en1x-dev) created the original [Taskbar Dock Animation](https://windhawk.net/mods/taskbar-dock-animation), including its animation concept and original implementation.
- [incconutwo](https://github.com/incconutwo) maintains Plus and contributed taskbar placement handling, multi-monitor improvements, smooth breathing transitions, and live updates.
- [PDSB001](https://github.com/PDSB001) contributed per-app rules, constrained wave layout, system tray filtering, Composition rendering, lifecycle fixes, and icon/indicator boundary corrections.

The source retains all three credits under the MIT license. / 源码保留三方署名，并沿用 MIT 许可证。
*/
// ==/WindhawkModReadme==


// ==WindhawkModSettings==
/*
- TaskbarPosition: auto
  $name: Taskbar position
  $name:zh-CN: 任务栏位置
  $name:uk-UA: Розташування панелі завдань
  $name:ja-JP: タスクバーの位置
  $name:ko-KR: 작업 표시줄 위치
  $name:pt-BR: Posição da barra de tarefas
  $name:it-IT: Posizione della barra delle applicazioni
  $description: Choose the taskbar's actual position if automatic detection gives the wrong animation direction. A manual choice applies to all taskbars; this setting does not move them.
  $description:zh-CN: 自动识别的动画方向不对时，选择任务栏实际所在位置。手动选择对所有任务栏生效，不会移动任务栏。
  $options:
  - auto: Automatic
  - bottom: Bottom
  - top: Top
  - left: Left
  - right: Right
  $options:zh-CN:
  - auto: 自动识别
  - bottom: 底部
  - top: 顶部
  - left: 左侧
  - right: 右侧
  $options:uk-UA:
  - auto: Автоматично
  - bottom: Знизу
  - top: Зверху
  - left: Ліворуч
  - right: Праворуч
  $options:ja-JP:
  - auto: 自動
  - bottom: 下
  - top: 上
  - left: 左
  - right: 右
  $options:ko-KR:
  - auto: 자동
  - bottom: 아래쪽
  - top: 위쪽
  - left: 왼쪽
  - right: 오른쪽
  $options:pt-BR:
  - auto: Automática
  - bottom: Inferior
  - top: Superior
  - left: Esquerda
  - right: Direita
  $options:it-IT:
  - auto: Automatica
  - bottom: In basso
  - top: In alto
  - left: A sinistra
  - right: A destra
- AnimationType: cosine
  $name: Animation Curve
  $name:uk-UA: Крива анімації
  $name:zh-CN: 动画曲线
  $name:ja-JP: アニメーション曲線
  $name:ko-KR: 애니메이션 곡선
  $name:pt-BR: Curva de animação
  $name:it-IT: Curva di animazione
  $options:
  - cosine: Cosine (smooth)
  - linear: Linear
  - exponential: Exponential (snappy)
  $options:uk-UA:
  - cosine: Косинусна (плавна)
  - linear: Лінійна
  - exponential: Експоненціальна (швидка)
  $options:zh-CN:
  - cosine: 余弦（平滑）
  - linear: 线性
  - exponential: 指数（灵敏）
  $options:ja-JP:
  - cosine: コサイン（なめらか）
  - linear: 線形
  - exponential: 指数（素早い）
  $options:ko-KR:
  - cosine: 코사인(부드럽게)
  - linear: 선형
  - exponential: 지수(빠르게)
  $options:pt-BR:
  - cosine: Cosseno (suave)
  - linear: Linear
  - exponential: Exponencial (rápida)
  $options:it-IT:
  - cosine: Coseno (fluida)
  - linear: Lineare
  - exponential: Esponenziale (reattiva)
- MaxScale: 130
  $name: Maximum scale (%)
  $name:uk-UA: Максимальний розмір (%)
  $name:zh-CN: 最大缩放（%）
  $name:ja-JP: 最大倍率（%）
  $name:ko-KR: 최대 확대 비율(%)
  $name:pt-BR: Escala máxima (%)
  $name:it-IT: Scala massima (%)
  $description: How large an icon can grow (e.g., 160 = +60%)
  $description:uk-UA: Наскільки сильно іконка може збільшитись (напр., 160 = +60%)
  $description:zh-CN: 图标最大可放大到多少（例如 160 = 增加 60%）
  $description:ja-JP: "アイコンの最大拡大率（例: 160 = +60%）"
  $description:ko-KR: "아이콘이 커질 수 있는 최대 크기 (예: 160 = +60%)"
  $description:pt-BR: "Até quanto o ícone pode aumentar (ex.: 160 = +60%)"
  $description:it-IT: "Quanto può ingrandirsi un’icona (es.: 160 = +60%)"
- EffectRadius: 100
  $name: Effect radius (px)
  $name:uk-UA: Радіус ефекту (пкс)
  $name:zh-CN: 效果半径（像素）
  $name:ja-JP: 効果半径（px）
  $name:ko-KR: 효과 반경(px)
  $name:pt-BR: Raio do efeito (px)
  $name:it-IT: Raggio dell’effetto (px)
  $description: Distance from the cursor where the animation is applied
  $description:uk-UA: Дистанція від курсора, на якій застосовується анімація
  $description:zh-CN: 距离光标多远范围内应用动画
  $description:ja-JP: カーソルからの距離に応じてアニメーションを適用します
  $description:ko-KR: 커서로부터 애니메이션이 적용되는 거리
  $description:pt-BR: Distância do cursor em que a animação é aplicada
  $description:it-IT: Distanza dal cursore entro cui si applica l’animazione
- SpacingFactor: 50
  $name: Spacing sensitivity (%)
  $name:uk-UA: Чутливість до проміжку (%)
  $name:zh-CN: 间距灵敏度（%）
  $name:ja-JP: 間隔の感度（%）
  $name:ko-KR: 간격 민감도(%)
  $name:pt-BR: Sensibilidade do espaçamento (%)
  $name:it-IT: Sensibilità spaziatura (%)
  $description: How much neighboring icons move apart during animation (default 50%)
  $description:uk-UA: Наскільки сусідні іконки розсуваються під час анімації (за замовчуванням 50%)
  $description:zh-CN: 动画时相邻图标拉开的程度（默认 50%）
  $description:ja-JP: アニメーション中に隣のアイコンが離れる度合い（既定 50%）
  $description:ko-KR: 애니메이션 중 인접 아이콘이 벌어지는 정도(기본 50%)
  $description:pt-BR: Quanto os ícones vizinhos se afastam durante a animação (padrão 50%)
  $description:it-IT: Quanto si allontanano le icone vicine durante l’animazione (predef. 50%)
- BounceDelay: 500
  $name: Bounce start delay (ms)
  $name:uk-UA: Затримка початку "дихання" (мс)
  $name:zh-CN: 弹跳开始延迟（毫秒）
  $name:ja-JP: バウンス開始遅延（ms）
  $name:ko-KR: 바운스 시작 지연(ms)
  $name:pt-BR: Atraso para iniciar o bounce (ms)
  $name:it-IT: Ritardo di inizio bounce (ms)
  $description: How long to wait after the cursor stops before starting the idle "breathing" animation (default 500ms)
  $description:uk-UA: Скільки чекати після зупинки курсора перед початком анімації "дихання" (за замовчуванням 500мс)
  $description:zh-CN: 光标停止后等待多久开始“呼吸”动画（默认 500ms）
  $description:ja-JP: カーソル停止後、待機時の「呼吸」アニメを開始するまでの遅延（既定 500ms）
  $description:ko-KR: 커서가 멈춘 뒤 ‘호흡’ 애니메이션을 시작하기까지 대기 시간(기본 500ms)
  $description:pt-BR: Quanto esperar após o cursor parar antes de iniciar a animação “respirar” (padrão 500ms)
  $description:it-IT: Quanto attendere dopo che il cursore si ferma prima di avviare l’animazione “respiro” (predef. 500ms)
- FocusDuration: 150
  $name: Focus animation duration (ms)
  $name:uk-UA: Тривалість анімації фокусу (мс)
  $name:zh-CN: 聚焦动画时长（毫秒）
  $name:ja-JP: フォーカスアニメ時間（ms）
  $name:ko-KR: 포커스 애니메이션 지속 시간(ms)
  $name:pt-BR: Duração da animação de foco (ms)
  $name:it-IT: Durata animazione focus (ms)
  $description: Duration of the fade-in and fade-out animation (default 150ms)
  $description:uk-UA: Тривалість анімації плавного з'явлення та згасання (за замовчуванням 150мс)
  $description:zh-CN: 淡入/淡出动画时长（默认 150ms）
  $description:ja-JP: フェードイン/アウトの時間（既定 150ms）
  $description:ko-KR: 페이드 인/아웃 애니메이션 지속 시간(기본 150ms)
  $description:pt-BR: Duração do fade-in e fade-out (padrão 150ms)
  $description:it-IT: Durata della dissolvenza in entrata/uscita (predef. 150ms)
- DisableVerticalBounce: false
  $name: Disable vertical "bounce" animation
  $name:uk-UA: Вимкнути вертикальне "дихання"
  $name:zh-CN: 禁用垂直“弹跳”动画
  $name:ja-JP: 垂直バウンスを無効化
  $name:ko-KR: 수직 바운스 애니메이션 비활성화
  $name:pt-BR: Desativar bounce vertical
  $name:it-IT: Disattiva bounce verticale
  $description: Disables the up/down "breathing" animation. Useful for vertical taskbars.
  $description:uk-UA: Вимикає анімацію "дихання" вгору/вниз. Корисно для вертикальних панелей.
  $description:zh-CN: 禁用上下“呼吸”动画。对垂直任务栏有用。
  $description:ja-JP: 上下の「呼吸」アニメを無効化します。縦型タスクバーに便利です。
  $description:ko-KR: 위/아래 ‘호흡’ 애니메이션을 비활성화합니다. 세로 작업 표시줄에 유용합니다.
  $description:pt-BR: Desativa a animação de “respirar” para cima/baixo. Útil para barras verticais.
  $description:it-IT: Disattiva l’animazione “respiro” su/giù. Utile per barre verticali.
- TaskbarLabelsMode: false
  $name: Taskbar Labels Compatibility
  $name:uk-UA: Сумісність із підписами (Labels)
  $name:zh-CN: 任务栏标签兼容模式
  $name:ja-JP: タスクバーラベル互換
  $name:ko-KR: 작업 표시줄 라벨 호환
  $name:pt-BR: Compatibilidade com rótulos
  $name:it-IT: Compatibilità etichette
  $description: Enable this if your taskbar shows window titles (rectangular icons) to fix animation centering.
  $description:uk-UA: Увімкніть, якщо ваша панель завдань відображає назви вікон (прямокутні кнопки), щоб виправити центрування.
  $description:zh-CN: 若任务栏显示窗口标题（矩形按钮），启用此项以修正动画居中。
  $description:ja-JP: タスクバーにウィンドウ名（矩形ボタン）が表示される場合、中央揃えを修正するために有効化します。
  $description:ko-KR: 작업 표시줄에 창 제목(직사각형 버튼)이 표시될 때 애니메이션 중앙 정렬을 수정합니다.
  $description:pt-BR: Ative se a barra mostrar títulos de janelas (ícones retangulares) para corrigir o alinhamento.
  $description:it-IT: Abilita se la barra mostra i titoli delle finestre (pulsanti rettangolari) per correggere la centratura.
- AppRules:
  - - AppId: ""
      $name: Application ID
      $name:zh-CN: 应用 ID
      $description: Exact AppUserModelID. Use Get-StartApps to find it.
      $description:zh-CN: 填写完整 AppUserModelID，可用 Get-StartApps 查找。
    - Mode: "0"
      $name: Animation mode
      $name:zh-CN: 动画模式
      $options:
      - "0": Wave
      - "1": Single icon
      - "2": Off
      $options:uk-UA:
      - "0": Хвиля
      - "1": Лише одна іконка
      - "2": Вимкнено
      $options:zh-CN:
      - "0": 波浪
      - "1": 仅放大悬停图标
      - "2": 关闭动画
      $options:ja-JP:
      - "0": 波状
      - "1": 単一アイコン
      - "2": オフ
      $options:ko-KR:
      - "0": 물결
      - "1": 아이콘 하나만
      - "2": 끄기
      $options:pt-BR:
      - "0": Onda
      - "1": Ícone único
      - "2": Desativado
      $options:it-IT:
      - "0": Onda
      - "1": Icona singola
      - "2": Disattivata
    - MaxScale: 0
      $name: Maximum scale (%)
      $name:zh-CN: 最大放大倍率（%）
      $description: 0 inherits the global value. Use 101–220 to override it.
      $description:zh-CN: 0 表示继承全局设置，101–220 表示自定义。
  $name: Per-app animation rules
  $name:zh-CN: 按应用配置动画
  $description: Up to 256 rules. The last rule for the same app ID wins.
  $description:zh-CN: 最多 256 条。相同应用 ID 以最后一条规则为准。
- HoveredIconOnly: false
  $name: Enlarge only the hovered icon
  $name:zh-CN: 仅放大悬停图标
  $description: Enlarge the button under the pointer without shifting neighboring icons.
  $description:zh-CN: 仅放大光标下的按钮，相邻图标不跟随移动。
- DisableWidgetsAnimation: false
  $name: Disable Widgets animation
  $name:zh-CN: 关闭小组件动画
  $description: Keep Widgets at their normal size without changing animation for other buttons.
  $description:zh-CN: 小组件保持原大小，其他按钮的动画设置不受影响。
- ExcludeSystemButtonsMode: all
  $name: Exclude system buttons
  $name:uk-UA: Ігнорувати системні кнопки
  $name:zh-CN: 排除系统按钮
  $name:ja-JP: システムボタンを除外
  $name:ko-KR: 시스템 버튼 제외
  $name:pt-BR: Excluir botões do sistema
  $name:it-IT: Escludi pulsanti di sistema
  $options:
  - all: Animate all eligible buttons
  - exclude_start: Exclude Start
  - apps_only: Animate app buttons only
  $options:uk-UA:
  - all: Усі доступні кнопки
  - exclude_start: Без кнопки «Пуск»
  - apps_only: Лише кнопки застосунків
  $options:zh-CN:
  - all: 所有可用按钮
  - exclude_start: 排除开始按钮
  - apps_only: 仅应用按钮
  $options:ja-JP:
  - all: 対象のボタンすべて
  - exclude_start: スタートを除外
  - apps_only: アプリボタンのみ
  $options:ko-KR:
  - all: 애니메이션 가능한 모든 버튼
  - exclude_start: 시작 버튼 제외
  - apps_only: 앱 버튼만
  $options:pt-BR:
  - all: Todos os botões compatíveis
  - exclude_start: Excluir o botão Iniciar
  - apps_only: Somente botões de aplicativos
  $options:it-IT:
  - all: Tutti i pulsanti compatibili
  - exclude_start: Escludi il pulsante Start
  - apps_only: Solo pulsanti delle app
- LerpSpeed: 60
  $name: Smoothing (Lerp speed)
  $name:uk-UA: Плавність (швидкість Lerp)
  $name:zh-CN: 平滑度（Lerp 速度）
  $name:ja-JP: スムージング（Lerp 速度）
  $name:ko-KR: 부드러움(Lerp 속도)
  $name:pt-BR: Suavização (velocidade do Lerp)
  $name:it-IT: Smussamento (velocità Lerp)
  $description: Higher = snappier, lower = smoother. 0 = disabled (direct)
  $description:uk-UA: Більше = швидше, менше = плавніше. 0 = вимкнути (напряму)
  $description:zh-CN: 越高越灵敏，越低越平滑。0=禁用（直接应用）
  $description:ja-JP: 大きいほどキビキビ、小さいほど滑らか。0=無効（直接適用）
  $description:ko-KR: 높을수록 빠릿함, 낮을수록 부드러움. 0=비활성화(직접)
  $description:pt-BR: Maior = mais rápido, menor = mais suave. 0 = desativado (direto)
  $description:it-IT: Più alto = più reattivo, più basso = più fluido. 0 = disattivato (diretto)
- DisableBounce: false
  $name: Disable bounce effect
  $name:uk-UA: Вимкнути bounce ефект
  $name:zh-CN: 禁用弹跳效果
  $name:ja-JP: バウンス効果を無効化
  $name:ko-KR: 바운스 효과 비활성화
  $name:pt-BR: Desativar efeito bounce
  $name:it-IT: Disattiva effetto bounce
  $description: Disables the idle "breathing" bounce entirely
  $description:uk-UA: Повністю вимикає bounce ("дихання")
  $description:zh-CN: 完全禁用空闲时的“呼吸”弹跳
  $description:ja-JP: 待機時の「呼吸」バウンスを完全に無効化します
  $description:ko-KR: 대기 상태 ‘호흡’ 바운스를 완전히 비활성화합니다
  $description:pt-BR: Desativa totalmente o bounce ocioso (“respirar”)
  $description:it-IT: Disattiva completamente il bounce inattivo (“respiro”)
*/
// ==/WindhawkModSettings==


#include <windhawk_utils.h>
#undef GetCurrentTime
#include <windows.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <winrt/Windows.UI.Xaml.h>
#include <winrt/Windows.UI.Xaml.Hosting.h>
#include <winrt/Windows.UI.Composition.h>
#include <winrt/Windows.UI.Xaml.Controls.h>
#include <winrt/Windows.UI.Xaml.Input.h>
#include <winrt/Windows.UI.Xaml.Media.h>
#include <winrt/Windows.UI.Input.h>
#include <vector>
#include <atomic>
#include <functional>
#include <limits>
#include <mutex>
#include <optional>
#include <utility>
#include <cmath>
#include <map>
#include <algorithm>
#include <chrono>
#include <unordered_map>
#include <memory>
#include <unordered_set>
#include <cstdint>
#include <cwctype>
#include <string>
#include <string_view>
#include <numbers>
#include <winrt/Windows.UI.Xaml.Automation.h>

using namespace winrt::Windows::UI::Xaml;
using namespace winrt::Windows::UI::Xaml::Media;
using namespace winrt::Windows::UI::Xaml::Automation;

enum class TaskbarEdge {
    Bottom,
    Top,
    Left,
    Right
};

// Settings container
struct {
    std::optional<TaskbarEdge> taskbarPosition;
    int animationType;
    double maxScale;
    int effectRadius;
    double spacingFactor;
    int bounceDelay;
    double focusDuration;
    bool disableVerticalBounce;
    bool taskbarLabelsMode;
    int excludeSystemButtonsMode;
    bool disableWidgetsAnimation;
    bool hoveredIconOnly;
    double lerpSpeed;
    bool disableBounce;
} g_settings;


// Global flags
std::atomic<bool> g_taskbarViewDllLoaded = false;

constexpr double MOUSE_STOP_THRESHOLD = 0.5;
constexpr double BOUNCE_PERIOD_MS = 1200.0;
constexpr double BOUNCE_SCALE_AMOUNT = 0.05;
constexpr double BOUNCE_TRANSLATE_Y = -4.0;


struct IconAnimState {
    double waveScale = 1.0;
    double waveTranslateX = 0.0;
    double requestedScale = 1.0;
};

enum class AppAnimationMode { Inherit, Wave, Single, Off };

struct AppAnimationRule {
    AppAnimationMode mode = AppAnimationMode::Inherit;
    double maxScale = 0.0;
};

using AppRuleMap = std::unordered_map<std::wstring, AppAnimationRule>;
std::shared_ptr<const AppRuleMap> g_appRules;

struct DockWaveItem {
    double start;
    double width;
    double pivot;
    double requestedScale;
    double priority;
    IconAnimState result;
};

struct IconPose {
    double waveScale = 1.0;
    double waveX = 0.0;
    double waveY = 0.0;
    double bounceScaleX = 1.0;
    double bounceScaleY = 1.0;
    double bounceX = 0.0;
    double bounceY = 0.0;
};

using winrt::Windows::Foundation::Numerics::float4x4;

struct IndicatorTransforms {
    winrt::weak_ref<FrameworkElement> element;
    winrt::Windows::UI::Composition::Visual visual{nullptr};
    float4x4 original = float4x4::identity();
    float4x4 applied = float4x4::identity();
    float crossOrigin = 0.0f;
    bool layoutValid = false;

    void Restore() {
        const auto current = visual.TransformMatrix();
        if (current == applied) {
            if (current != original) visual.TransformMatrix(original);
        } else {
            original = current;
        }
        applied = original;
    }
};

struct CrossAxisInsets {
    float start = 0.0f;
    float end = 0.0f;
};

static void MergeIndicatorInsets(CrossAxisInsets& shared, float extent,
                                  float lower, float upper) {
    if (!(extent > 0.0f && lower >= 0.0f && upper <= extent && upper > lower)) return;
    shared.start = std::max(shared.start, lower / extent);
    shared.end = std::max(shared.end, (extent - upper) / extent);
}

// Cancel the parent's cross-axis effect around the indicator's native origin.
// Along the wave axis, the indicator continues to follow its button.
static float IndicatorCrossAxisTranslation(float origin, float scale, float shift) {
    return (origin - shift) / scale - origin;
}

// Keep painted content inside the native cross-axis slot when it fits. This
// adjusts translation only: the requested scale and wave layout stay intact.
static float FitIconCrossAxis(float start, float end, float extent,
                              float scale, float translation,
                              float lower = 0.0f, float upper = -1.0f) {
    if (upper < 0.0f) upper = extent;
    if (!(lower >= 0.0f && upper <= extent && upper > lower)) return translation;
    if (!(extent > 0.0f && end > start && start >= 0.0f && end <= extent) ||
        !std::isfinite(scale) || !std::isfinite(translation) || scale <= 0.0f) {
        return translation;
    }
    const float minimum = lower - start * scale;
    const float maximum = upper - end * scale;
    if (minimum > maximum) {
        // Oversized content cannot fit without changing scale or its host.
        // Center the unavoidable overflow instead of clipping one side early.
        return (minimum + maximum) / 2.0f;
    }
    return std::clamp(translation, minimum, maximum);
}

struct IconTransforms {
    winrt::Windows::UI::Composition::Visual visual{nullptr};
    float4x4 original = float4x4::identity();
    float4x4 applied = float4x4::identity();
    float pivotX = 0.0f;
    float pivotY = 0.0f;
    bool vertical = false;
    float crossStart = 0.0f;
    float crossEnd = 0.0f;
    float crossExtent = 0.0f;
    winrt::weak_ref<FrameworkElement> button;
    std::vector<IndicatorTransforms> indicators;
    CrossAxisInsets cachedIndicatorInsets;
    bool indicatorCacheValid = false;

    CrossAxisInsets MeasureIndicatorInsets(bool refresh) {
        if (indicatorCacheValid && !refresh) return cachedIndicatorInsets;
        if (indicators.empty()) {
            indicatorCacheValid = true;
            return cachedIndicatorInsets = {};
        }
        auto root = button.get();
        float lower = 0.0f;
        float upper = crossExtent;
        for (auto& indicator : indicators) {
            indicator.layoutValid = false;
            try {
                auto element = indicator.element.get();
                if (!root || !element) continue;
                auto parent = VisualTreeHelper::GetParent(element).try_as<FrameworkElement>();
                if (!parent) continue;
                const auto offset = element.ActualOffset();
                const auto transform = parent.TransformToVisual(root);
                const auto origin = transform.TransformPoint({offset.x, offset.y});
                indicator.crossOrigin = vertical ? origin.X : origin.Y;
                indicator.layoutValid = true;
                const auto bounds = transform.TransformBounds({
                    offset.x, offset.y, static_cast<float>(element.ActualWidth()),
                    static_cast<float>(element.ActualHeight())});
                const float start = vertical ? bounds.X : bounds.Y;
                const float size = vertical ? bounds.Width : bounds.Height;
                // Reserve visible native strips, not a full-size indicator host.
                // Without this, a top-anchored glyph can cover the fixed strip.
                if (element.Visibility() == Visibility::Visible && size > 0.0f &&
                    size < crossExtent / 2.0f && start >= 0.0f && start + size <= crossExtent) {
                    constexpr float gap = 1.0f;
                    if (start >= crossEnd && crossEnd > crossStart) upper = std::min(upper, start - gap);
                    else if (start + size <= crossStart) lower = std::max(lower, start + size + gap);
                }
            } catch (const winrt::hresult_error&) {
            }
        }
        CrossAxisInsets result;
        MergeIndicatorInsets(result, crossExtent, lower, upper);
        cachedIndicatorInsets = result;
        indicatorCacheValid = true;
        return result;
    }

    void Apply(const IconPose& pose, const CrossAxisInsets& sharedInsets) {
        const float sx = static_cast<float>(pose.waveScale * pose.bounceScaleX);
        const float sy = static_cast<float>(pose.waveScale * pose.bounceScaleY);
        float dx = pivotX * (1.0f - sx) +
                         static_cast<float>(pose.waveX * pose.bounceScaleX + pose.bounceX);
        float dy = pivotY * (1.0f - sy) +
                         static_cast<float>(pose.waveY * pose.bounceScaleY + pose.bounceY);
        const float lower = sharedInsets.start * crossExtent;
        const float upper = (1.0f - sharedInsets.end) * crossExtent;
        if (vertical) dx = FitIconCrossAxis(crossStart, crossEnd, crossExtent, sx, dx, lower, upper);
        else dy = FitIconCrossAxis(crossStart, crossEnd, crossExtent, sy, dy, lower, upper);
        const float4x4 effect{sx, 0, 0, 0, 0, sy, 0, 0, 0, 0, 1, 0, dx, dy, 0, 1};
        const auto next = effect * original;
        if (next != applied) {
            visual.TransformMatrix(next);
            applied = next;
        }
        if (!indicators.empty() && button.get()) {
            for (auto& indicator : indicators) {
                try {
                    if (!indicator.layoutValid) continue;
                    const float scale = vertical ? sx : sy;
                    const float shift = vertical ? dx : dy;
                    if (!(scale > 0.0f)) continue;
                    const float translation = IndicatorCrossAxisTranslation(
                        indicator.crossOrigin, scale, shift);
                    const float inverse = 1.0f / scale;
                    const float4x4 counter = vertical
                        ? float4x4{inverse,0,0,0, 0,1,0,0, 0,0,1,0, translation,0,0,1}
                        : float4x4{1,0,0,0, 0,inverse,0,0, 0,0,1,0, 0,translation,0,1};
                    const auto current = indicator.visual.TransformMatrix();
                    if (current != indicator.applied) indicator.original = current;
                    const auto matrix = indicator.original * counter;
                    if (matrix != current) indicator.visual.TransformMatrix(matrix);
                    indicator.applied = matrix;
                } catch (const winrt::hresult_error&) {
                    // Indicators can be replaced while a task changes state.
                }
            }
        }
    }

    void Restore() {
        for (auto& indicator : indicators) {
            try { indicator.Restore(); } catch (const winrt::hresult_error&) {}
        }
        const auto current = visual.TransformMatrix();
        if (current == applied) {
            if (current != original) visual.TransformMatrix(original);
        } else {
            // Explorer or another owner changed the visual since our last write.
            original = current;
        }
        applied = original;
    }
};

static void ApplyIconPose(IconTransforms& transforms, const IconPose& pose,
                          AppAnimationMode mode, const CrossAxisInsets& insets) {
    if (mode == AppAnimationMode::Off) transforms.Restore();
    else transforms.Apply(pose, insets);
}

void SetIconPivot(IconTransforms& transforms, FrameworkElement const& element,
                  bool vertical, TaskbarEdge edge) {
    const float width = static_cast<float>(element.ActualWidth());
    const float height = static_cast<float>(element.ActualHeight());
    transforms.vertical = vertical;
    transforms.crossExtent = vertical ? width : height;
    transforms.pivotX = vertical ? (edge == TaskbarEdge::Left ? 0.0f : width)
        : (g_settings.taskbarLabelsMode && width > 0.0f ? 24.0f : width / 2.0f);
    transforms.pivotY = vertical
        ? (g_settings.taskbarLabelsMode && height > 0.0f ? 24.0f : height / 2.0f)
        : (g_settings.disableVerticalBounce ? height / 2.0f
                                            : (edge == TaskbarEdge::Top ? 0.0f : height));
}

// Wide system controls paint a background beyond their glyph/text bounds.
// Reserve their whole slot instead of treating that background as empty space.
static bool UseFullSlotFootprint(bool isApplication, double extent, double crossExtent) {
    return !isApplication && crossExtent > 0.0 && extent > crossExtent * 1.5;
}

static double FixedSlotScaleLimit(double start, double width, double pivot,
                                  double lower, double upper) {
    double limit = std::numeric_limits<double>::infinity();
    if (pivot > 0.0 && std::isfinite(lower)) limit = std::min(limit, 1.0 + (start - lower) / pivot);
    if (width > pivot && std::isfinite(upper)) limit = std::min(limit, (upper - start - pivot) / (width - pivot));
    return std::max(1.0, limit);
}

// Per-monitor context
struct TaskbarIconInfo {
    winrt::weak_ref<FrameworkElement> element;
    double originalCenterX = 0.0;
    double elementWidth = 0.0;
    double footprintStart = 0.0;
    double footprintEnd = 1.0;
    bool fullSlotFootprint = false;
    IconAnimState state;
    IconTransforms transforms;
    AppAnimationRule rule;
};

struct HostSignature {
    int count = -1;
    double width = -1.0;
    uint64_t orderHash = 0;
};

// Event callbacks retain only this signal, never a context or taskbar visual.
struct LayoutDirtySignal {
    std::atomic<bool> contentDirty{false};
    std::atomic<bool> geometryDirty{true};
    std::atomic<bool> indicatorsDirty{true};
};

struct ContentSizeWatch {
    winrt::weak_ref<FrameworkElement> element;
    winrt::event_token token;
};

struct IndicatorVisibilityWatch {
    winrt::weak_ref<FrameworkElement> element;
    int64_t token;
};

static bool ShouldRefreshGeometry(bool subscribed, bool dirty,
                                  std::chrono::milliseconds elapsed) {
    return !subscribed || dirty || elapsed >= std::chrono::milliseconds(1000);
}

struct DockAnimationContext {
    bool isInitialized = false;
    winrt::weak_ref<FrameworkElement> taskbarFrame;
    winrt::weak_ref<FrameworkElement> iconHost;
    std::vector<TaskbarIconInfo> icons;
    std::vector<DockWaveItem> waveScratch;
    CrossAxisInsets indicatorInsets;
    bool measureIndicators = true;
    std::shared_ptr<LayoutDirtySignal> layoutSignal;
    winrt::event_token layoutToken{};
    bool layoutSubscribed = false;
    std::vector<IndicatorVisibilityWatch> indicatorVisibilityWatches;
    std::vector<ContentSizeWatch> contentSizeWatches;
    bool contentNeedsRefresh = false;
    std::chrono::steady_clock::time_point lastContentCheck{};
    std::chrono::steady_clock::time_point lastGeometryCheck{};
    bool needsFrame = true;
    double lastLayoutMouse = -1.0;

    HostSignature lastSig;
    std::chrono::steady_clock::time_point lastDirtyCheck{};

    TaskbarEdge edge = TaskbarEdge::Bottom;
    TaskbarEdge lastLayoutEdge = TaskbarEdge::Bottom;
    bool isVertical = false;
    HWND hWnd = nullptr;
};

struct TaskbarThreadState {
    std::map<void*, DockAnimationContext> contexts;
    HWND renderingWindow = nullptr;
    winrt::event_token renderingToken{};
    void* activeContextKey = nullptr;
    bool mouseInside = false;
    bool bouncing = false;
    double mouseX = -1.0;
    double intensity = 0.0;
    double bounceIntensity = 0.0;
    std::chrono::steady_clock::time_point lastMove{};
    std::chrono::steady_clock::time_point lastRender{};
    std::chrono::steady_clock::time_point bounceStart{};
    uint64_t settingsRevision = 0;
};

// Serialize settings publication and lifecycle changes with pointer and render
// callbacks. Window-thread dispatch must happen outside this lock.
std::recursive_mutex g_animationMutex;
// Explorer can terminate without Wh_ModBeforeUninit. Skip static destruction
// so it cannot release taskbar-owned visuals from the terminating thread.
[[clang::no_destroy]] std::map<DWORD, TaskbarThreadState> g_taskbarThreads;
std::atomic<bool> g_unloading = false;
uint64_t g_settingsRevision = 0;

void ResetAllIconScales(std::vector<TaskbarIconInfo>& icons);
void RefreshIconPositions(DockAnimationContext& ctx);
void OnCompositionTargetRendering();

// Hold a spare loader reference before any callback can be registered. The
// engine still holds its own reference while Wh_ModUninit runs, so releasing
// the spare on the normal path cannot unload code underneath this function.
HMODULE g_callbackModuleReference = nullptr;
std::atomic<bool> g_preserveCallbackModule = false;

bool AcquireCallbackModuleReference() {
    return GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS,
        reinterpret_cast<LPCWSTR>(&AcquireCallbackModuleReference), &g_callbackModuleReference);
}

void PreserveCallbackModule() {
    if (!g_preserveCallbackModule.exchange(true)) {
        Wh_Log(L"DockAnimation: Callback cleanup failed; retaining this DLL until Explorer exits.");
    }
}

void ReleaseCallbackModuleReference() {
    if (!g_preserveCallbackModule && g_callbackModuleReference) {
        const auto module = std::exchange(g_callbackModuleReference, nullptr);
        FreeLibrary(module);
    }
}

enum class PendingSubscriptionKind { Layout, Visibility, Size, Rendering };
struct PendingSubscription {
    PendingSubscriptionKind kind;
    winrt::weak_ref<FrameworkElement> element;
    int64_t token;
};
// Retry only on the owning UI thread. Failed cleanup never releases UI state
// or its delegate code on the engine thread.
[[clang::no_destroy]] std::map<DWORD, std::vector<PendingSubscription>> g_pendingSubscriptions;

void QueuePendingSubscription(PendingSubscriptionKind kind,
                              winrt::weak_ref<FrameworkElement> element, int64_t token) {
    PreserveCallbackModule();
    try {
        g_pendingSubscriptions[GetCurrentThreadId()].push_back({kind, element, token});
    } catch (...) {
        // The spare module reference still protects any live delegate if an
        // allocation fails while saving its retry token.
        Wh_Log(L"DockAnimation: Could not store a callback cleanup token.");
    }
}

void RetryPendingSubscriptions() {
    auto thread = g_pendingSubscriptions.find(GetCurrentThreadId());
    if (thread == g_pendingSubscriptions.end()) return;
    auto& pending = thread->second;
    for (auto it = pending.begin(); it != pending.end();) {
        try {
            if (it->kind == PendingSubscriptionKind::Rendering) {
                Media::CompositionTarget::Rendering(winrt::event_token{it->token});
            } else if (auto element = it->element.get()) {
                switch (it->kind) {
                    case PendingSubscriptionKind::Layout:
                        element.LayoutUpdated(winrt::event_token{it->token}); break;
                    case PendingSubscriptionKind::Visibility:
                        element.UnregisterPropertyChangedCallback(UIElement::VisibilityProperty(), it->token); break;
                    case PendingSubscriptionKind::Size:
                        element.SizeChanged(winrt::event_token{it->token}); break;
                    default: break;
                }
            }
            it = pending.erase(it);
        } catch (const winrt::hresult_error&) {
            ++it;
        }
    }
    if (pending.empty()) g_pendingSubscriptions.erase(thread);
}

void StopRendering(TaskbarThreadState& state) {
    if (state.renderingWindow) {
        try {
            Media::CompositionTarget::Rendering(state.renderingToken);
        } catch (const winrt::hresult_error&) {
            QueuePendingSubscription(PendingSubscriptionKind::Rendering, {}, state.renderingToken.value);
        }
        state.renderingWindow = nullptr;
    }
}

void StopContentSizeWatch(DockAnimationContext& ctx) {
    RetryPendingSubscriptions();
    for (const auto& watch : ctx.contentSizeWatches) {
        try {
            if (auto element = watch.element.get()) element.SizeChanged(watch.token);
        } catch (const winrt::hresult_error&) {
            QueuePendingSubscription(PendingSubscriptionKind::Size, watch.element, watch.token.value);
        }
    }
    ctx.contentSizeWatches.clear();
}

void StopLayoutWatch(DockAnimationContext& ctx) {
    ctx.layoutSignal.reset();
    StopContentSizeWatch(ctx);
    if (ctx.layoutSubscribed) {
        try {
            if (auto frame = ctx.taskbarFrame.get()) frame.LayoutUpdated(ctx.layoutToken);
        } catch (const winrt::hresult_error&) {
            QueuePendingSubscription(PendingSubscriptionKind::Layout, ctx.taskbarFrame, ctx.layoutToken.value);
        }
        ctx.layoutSubscribed = false;
    }
    for (const auto& watch : ctx.indicatorVisibilityWatches) {
        try {
            if (auto element = watch.element.get()) {
                element.UnregisterPropertyChangedCallback(UIElement::VisibilityProperty(), watch.token);
            }
        } catch (const winrt::hresult_error&) {
            QueuePendingSubscription(PendingSubscriptionKind::Visibility, watch.element, watch.token);
        }
    }
    ctx.indicatorVisibilityWatches.clear();
}

void StartLayoutWatch(DockAnimationContext& ctx, FrameworkElement const& frame) {
    // Do not accumulate new subscriptions while failed old ones await retry.
    if (g_pendingSubscriptions.contains(GetCurrentThreadId())) return;
    ctx.layoutSignal = std::make_shared<LayoutDirtySignal>();
    const std::weak_ptr<LayoutDirtySignal> weak = ctx.layoutSignal;
    try {
        ctx.layoutToken = frame.LayoutUpdated([weak](auto const&, auto const&) {
            if (auto signal = weak.lock()) signal->geometryDirty.store(true, std::memory_order_relaxed);
        });
        ctx.layoutSubscribed = true;
    } catch (const winrt::hresult_error&) {
        // The periodic path keeps the previous 120-ms behavior if subscribing fails.
    }
}

void WatchIndicatorVisibility(DockAnimationContext& ctx, FrameworkElement const& element) {
    if (!ctx.layoutSignal || g_pendingSubscriptions.contains(GetCurrentThreadId())) return;
    const std::weak_ptr<LayoutDirtySignal> weak = ctx.layoutSignal;
    try {
        // Reserve storage before registering so an allocation failure cannot
        // leave a registered callback without its cleanup token.
        ctx.indicatorVisibilityWatches.push_back({element, 0});
        auto& watch = ctx.indicatorVisibilityWatches.back();
        try {
            watch.token = element.RegisterPropertyChangedCallback(UIElement::VisibilityProperty(),
                [weak](auto const&, auto const&) {
                    if (auto signal = weak.lock()) {
                        signal->indicatorsDirty.store(true, std::memory_order_relaxed);
                        signal->geometryDirty.store(true, std::memory_order_relaxed);
                    }
                });
        } catch (...) {
            ctx.indicatorVisibilityWatches.pop_back();
            throw;
        }
    } catch (const winrt::hresult_error&) {}
}

void WatchContentSize(DockAnimationContext& ctx, FrameworkElement const& element) {
    if (!ctx.layoutSignal || g_pendingSubscriptions.contains(GetCurrentThreadId())) return;
    const std::weak_ptr<LayoutDirtySignal> weak = ctx.layoutSignal;
    try {
        ctx.contentSizeWatches.push_back({element, {}});
        try {
            ctx.contentSizeWatches.back().token = element.SizeChanged([weak](auto const&, auto const&) {
                if (auto signal = weak.lock()) {
                    signal->contentDirty.store(true, std::memory_order_relaxed);
                    signal->geometryDirty.store(true, std::memory_order_relaxed);
                }
            });
        } catch (...) {
            ctx.contentSizeWatches.pop_back();
            throw;
        }
    } catch (const winrt::hresult_error&) {}
}

void ResetContext(DockAnimationContext& ctx) {
    StopLayoutWatch(ctx);
    ResetAllIconScales(ctx.icons);
    ctx.isInitialized = false;
    ctx.needsFrame = true;
    ctx.icons.clear();
    ctx.indicatorInsets = {};
    ctx.measureIndicators = true;
    ctx.contentNeedsRefresh = false;
}

HMODULE GetTaskbarViewModuleHandle();
bool HookTaskbarViewDllSymbols(HMODULE module);
static bool RebaseIconGeometryFast(DockAnimationContext& ctx);

HWND GetCurrentThreadTrayWindow() {
    const DWORD thread = GetCurrentThreadId();
    POINT cursor{};
    const HMONITOR monitor = GetCursorPos(&cursor)
        ? MonitorFromPoint(cursor, MONITOR_DEFAULTTONULL)
        : nullptr;
    HWND fallback = nullptr;
    const auto matchesMonitor = [&](HWND window) {
        if (!window || GetWindowThreadProcessId(window, nullptr) != thread) return false;
        if (!fallback) fallback = window;
        return monitor && MonitorFromWindow(window, MONITOR_DEFAULTTONULL) == monitor;
    };

    HWND primary = FindWindow(L"Shell_TrayWnd", nullptr);
    if (matchesMonitor(primary)) return primary;
    HWND secondary = nullptr;
    while ((secondary = FindWindowEx(nullptr, secondary, L"Shell_SecondaryTrayWnd", nullptr))) {
        if (matchesMonitor(secondary)) return secondary;
    }
    return fallback;
}

static std::optional<TaskbarEdge> ParseTaskbarPosition(std::wstring_view value) {
    if (value == L"bottom") return TaskbarEdge::Bottom;
    if (value == L"top") return TaskbarEdge::Top;
    if (value == L"left") return TaskbarEdge::Left;
    if (value == L"right") return TaskbarEdge::Right;
    return std::nullopt;
}

static void ApplyTaskbarEdge(DockAnimationContext& ctx, TaskbarEdge edge) {
    if (ctx.edge != edge) {
        // Cached origins, footprints, pivots and indicator corrections belong
        // to the previous axis. Never reuse them for even the first new frame.
        ResetContext(ctx);
        ctx.lastLayoutMouse = -1.0;
    }
    ctx.edge = edge;
    ctx.isVertical = edge == TaskbarEdge::Left || edge == TaskbarEdge::Right;
}

void UpdateTaskbarEdge(DockAnimationContext& ctx) {
    auto frame = ctx.taskbarFrame.get();
    if (!frame) return;

    HWND hWnd = ctx.hWnd;
    if (!hWnd || !IsWindow(hWnd)) {
        hWnd = GetCurrentThreadTrayWindow();
        ctx.hWnd = hWnd;
    }

    if (g_settings.taskbarPosition) {
        ApplyTaskbarEdge(ctx, *g_settings.taskbarPosition);
        return;
    }

    TaskbarEdge edge = ctx.edge;
    RECT rect{};
    MONITORINFO mi{sizeof(mi)};
    if (hWnd && GetWindowRect(hWnd, &rect) &&
        GetMonitorInfoW(MonitorFromWindow(hWnd, MONITOR_DEFAULTTONEAREST), &mi)) {
        if (rect.right - rect.left < rect.bottom - rect.top) {
            edge = rect.left <= mi.rcMonitor.left + (mi.rcMonitor.right - mi.rcMonitor.left) / 2
                ? TaskbarEdge::Left : TaskbarEdge::Right;
        } else {
            edge = rect.top <= mi.rcMonitor.top + (mi.rcMonitor.bottom - mi.rcMonitor.top) / 2
                ? TaskbarEdge::Top : TaskbarEdge::Bottom;
        }
    } else {
        // When geometry is temporarily unavailable, preserve the known side
        // if its axis still agrees with the live XAML layout.
        const bool vertical = frame.ActualWidth() < frame.ActualHeight();
        if (vertical != ctx.isVertical) edge = vertical ? TaskbarEdge::Left : TaskbarEdge::Bottom;
    }
    ApplyTaskbarEdge(ctx, edge);
}

// Simple visual tree helpers
FrameworkElement EnumChildElements(
    FrameworkElement element,
    std::function<bool(FrameworkElement)> enumCallback) {
    int childrenCount = VisualTreeHelper::GetChildrenCount(element);
    for (int i = 0; i < childrenCount; i++) {
        auto child = VisualTreeHelper::GetChild(element, i).try_as<FrameworkElement>();
        if (!child) continue;
        if (enumCallback(child)) return child;
    }
    return nullptr;
}

FrameworkElement FindChildByClassName(FrameworkElement element,
                                          PCWSTR className) {
    if (!element) return nullptr;
    return EnumChildElements(element, [className](FrameworkElement child) {
        return winrt::get_class_name(child) == className;
    });
}

// Animation math (cosine falloff)
double CalculateScale(double distance, double radius, double maxScale) {
    if (distance > radius) return 1.0;

    double t = distance / radius;
    double factor = 0.0;

    switch (g_settings.animationType) {
        case 1: // Linear
            factor = 1.0 - t;
            break;
        case 2: // Exponential
            factor = pow(1.0 - t, 3);
            break;
        case 0: // Cosine
        default:
            factor = (cos(t * std::numbers::pi) + 1.0) / 2.0;
            break;
    }
    if (factor < 0) factor = 0;
    return (maxScale - 1.0) * factor + 1.0;
}

// Work in one dimension so the same layout serves all four taskbar edges.
// Layout uses painted icon widths when available and native slot widths for
// fixed buttons. Gaps can shrink before any requested zoom is sacrificed.
void SolveDockWave(std::vector<DockWaveItem>& items, double lower, double upper,
                   double spacingFactor) {
    const double nativeStart = items.front().start;
    const double nativeEnd = items.back().start + items.back().width;
    lower = std::min(lower, nativeStart);
    upper = std::max(upper, nativeEnd);
    const double capacity = upper - lower;

    double minimumWidth = 0.0;
    double requestedGrowth = 0.0;
    double lastEnd = nativeStart;
    for (auto& item : items) {
        minimumWidth += item.width + std::min(0.0, item.start - lastEnd);
        requestedGrowth += item.width * (item.requestedScale - 1.0);
        lastEnd = item.start + item.width;
    }
    const double growthBudget = std::max(0.0, capacity - minimumWidth);

    // Find the largest weighted allocation that fits. Nearer buttons get a
    // larger share while the allocation remains continuous as the cursor moves.
    double fraction = 1.0;
    if (requestedGrowth > growthBudget) {
        double low = 0.0;
        double high = 1.0;
        for (int step = 0; step < 24; ++step) {
            const double trial = (low + high) / 2.0;
            double used = 0.0;
            for (const auto& item : items) {
                used += item.width * (item.requestedScale - 1.0) *
                        std::min(1.0, trial * item.priority);
            }
            if (used <= growthBudget) low = trial;
            else high = trial;
        }
        fraction = low;
    }

    double preferredGaps = 0.0;
    double occupied = minimumWidth;
    lastEnd = nativeStart;
    double lastGrowth = 0.0;
    for (auto& item : items) {
        item.result.waveScale = 1.0 + (item.requestedScale - 1.0) *
                                      std::min(1.0, fraction * item.priority);
        const double growth = item.width * (item.result.waveScale - 1.0);
        if (&item != &items.front()) {
            preferredGaps += std::max(0.0, item.start - lastEnd) +
                             (lastGrowth + growth) * spacingFactor / 2.0;
        }
        occupied += growth;
        lastEnd = item.start + item.width;
        lastGrowth = growth;
    }
    const double gapRatio = preferredGaps > 0.0
        ? std::clamp((capacity - occupied) / preferredGaps, 0.0, 1.0)
        : 0.0;
    const double layoutWidth = occupied + preferredGaps * gapRatio;

    double cursor = nativeStart - (layoutWidth - (nativeEnd - nativeStart)) / 2.0;
    if (std::isfinite(lower) && !std::isfinite(upper)) cursor = nativeStart;
    if (!std::isfinite(lower) && std::isfinite(upper)) cursor = nativeEnd - layoutWidth;
    cursor = std::clamp(cursor, lower, std::max(lower, upper - layoutWidth));

    lastEnd = nativeStart;
    lastGrowth = 0.0;
    for (auto& item : items) {
        const double growth = item.width * (item.result.waveScale - 1.0);
        if (&item != &items.front()) {
            const double gap = item.start - lastEnd;
            cursor += std::min(0.0, gap) + gapRatio *
                      (std::max(0.0, gap) + (lastGrowth + growth) * spacingFactor / 2.0);
        }
        item.result.waveTranslateX = cursor - item.start +
                                    item.pivot * (item.result.waveScale - 1.0);
        cursor += item.width + growth;
        lastEnd = item.start + item.width;
        lastGrowth = growth;
    }
}

bool ApplyAnimation(double mouseX, DockAnimationContext& ctx, double intensity,
                    double dtSec, const TaskbarThreadState& state) {
    const size_t count = ctx.icons.size();
    const double alpha = g_settings.lerpSpeed > 0.0
        ? std::clamp(1.0 - std::exp(-g_settings.lerpSpeed * dtSec), 0.0, 1.0)
        : 1.0;
    const auto modeOf = [](const TaskbarIconInfo& icon) {
        return icon.rule.mode == AppAnimationMode::Inherit
            ? (g_settings.hoveredIconOnly ? AppAnimationMode::Single : AppAnimationMode::Wave)
            : icon.rule.mode;
    };
    const auto startOf = [](const TaskbarIconInfo& icon) {
        return icon.originalCenterX -
            (g_settings.taskbarLabelsMode ? 0.0 : icon.elementWidth / 2.0);
    };
    const auto maxScaleOf = [](const TaskbarIconInfo& icon) {
        return icon.rule.maxScale > 0 ? icon.rule.maxScale : g_settings.maxScale;
    };
    bool settling = false;
    const auto requestedScale = [&](const TaskbarIconInfo& icon, double scale) {
        const double target = 1.0 + (scale - 1.0) * intensity;
        const double previous = icon.state.requestedScale;
        const double next = previous + (target - previous) * alpha;
        if (std::abs(next - target) < 0.0001) return target;
        settling = true;
        return next;
    };

    size_t closestIconIndex = (size_t)-1;
    double minDistance = g_settings.effectRadius + 1.0;
    constexpr double unbounded = std::numeric_limits<double>::infinity();
    auto& group = ctx.waveScratch;
    for (size_t i = 0; i < count;) {
        auto& icon = ctx.icons[i];
        const auto mode = modeOf(icon);
        if (mode != AppAnimationMode::Wave) {
            if (mode == AppAnimationMode::Off) {
                icon.state = {};
            } else {
                const double start = startOf(icon);
                const bool hovered = mouseX >= start && mouseX < start + icon.elementWidth;
                if (hovered) {
                    closestIconIndex = i;
                    minDistance = 0.0;
                }
                double limit = std::numeric_limits<double>::infinity();
                if (icon.fullSlotFootprint) {
                    const double lower = i > 0
                        ? startOf(ctx.icons[i - 1]) + ctx.icons[i - 1].elementWidth : -unbounded;
                    const double upper = i + 1 < count ? startOf(ctx.icons[i + 1]) : unbounded;
                    const double pivot = ctx.isVertical ? icon.transforms.pivotY : icon.transforms.pivotX;
                    limit = FixedSlotScaleLimit(start, icon.elementWidth, pivot, lower, upper);
                }
                const double target = hovered ? std::min(maxScaleOf(icon), limit) : 1.0;
                const double scale = std::min(limit, requestedScale(icon, target));
                icon.state = {scale, 0.0, scale};
            }
            ++i;
            continue;
        }

        const size_t first = i;
        while (i < count && modeOf(ctx.icons[i]) == AppAnimationMode::Wave) ++i;
        const double lower = first > 0
            ? startOf(ctx.icons[first - 1]) + ctx.icons[first - 1].elementWidth : -unbounded;
        const double upper = i < count ? startOf(ctx.icons[i]) : unbounded;
        const bool active = mouseX >= lower && mouseX < upper;
        group.clear();
        for (size_t j = first; j < i; ++j) {
            const auto& button = ctx.icons[j];
            const double start = startOf(button);
            const double distance = (g_settings.taskbarLabelsMode || button.fullSlotFootprint)
                ? std::max({0.0, start - mouseX, mouseX - start - button.elementWidth})
                : std::abs(mouseX - button.originalCenterX);
            const double scale = active ? CalculateScale(distance, g_settings.effectRadius,
                                                         maxScaleOf(button)) : 1.0;
            const double proximity = std::max(0.0, 1.0 - distance / g_settings.effectRadius);
            const double inset = button.footprintStart * button.elementWidth;
            group.push_back({
                start + inset,
                (button.footprintEnd - button.footprintStart) * button.elementWidth,
                (g_settings.taskbarLabelsMode ? 24.0 : button.elementWidth / 2.0) - inset,
                requestedScale(button, scale),
                1.0 + 12.0 * proximity * proximity * proximity * proximity,
                {},
            });
            if (active && button.elementWidth > 0.0 && distance < minDistance) {
                minDistance = distance;
                closestIconIndex = j;
            }
        }
        SolveDockWave(group, lower, upper, g_settings.spacingFactor);
        for (size_t j = first; j < i; ++j) {
            const auto& item = group[j - first];
            ctx.icons[j].state = item.result;
            ctx.icons[j].state.requestedScale = item.requestedScale;
        }
    }

    double bounceScaleFactor = 1.0;
    double bounceTranslateOffset = 0.0;

    double currentBounceIntensity = state.bounceIntensity;

    if (currentBounceIntensity > 0.0 && closestIconIndex != (size_t)-1 &&
        minDistance < (g_settings.effectRadius / 2.0)) {
        auto elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                            std::chrono::steady_clock::now() - state.bounceStart)
                            .count();
        double t = std::fmod(elapsed_ms, BOUNCE_PERIOD_MS) / BOUNCE_PERIOD_MS;
        double normalizedWave = std::sin(t * std::numbers::pi);
        bounceScaleFactor = 1.0 + (normalizedWave * BOUNCE_SCALE_AMOUNT * currentBounceIntensity);
        bounceTranslateOffset = normalizedWave * BOUNCE_TRANSLATE_Y * currentBounceIntensity;

        if (ctx.isVertical) {
            if (ctx.edge == TaskbarEdge::Left) {
                bounceTranslateOffset *= -1.0;
            }
        } else {
            if (ctx.edge == TaskbarEdge::Top) {
                bounceTranslateOffset *= -1.0;
            }
        }
    }

    // Every animated button uses the same reserved band, including apps with
    // no running strip. Retain it for this context so state changes do not
    // make the glyphs jump between different cross-axis alignments.
    for (auto& icon : ctx.icons) {
        const auto insets = icon.transforms.MeasureIndicatorInsets(ctx.measureIndicators);
        ctx.indicatorInsets.start = std::max(ctx.indicatorInsets.start, insets.start);
        ctx.indicatorInsets.end = std::max(ctx.indicatorInsets.end, insets.end);
    }
    ctx.measureIndicators = false;

    for (size_t i = 0; i < count; ++i) {
        auto& icon = ctx.icons[i];
        IconPose pose;
        pose.waveScale = icon.state.waveScale;
        if (ctx.isVertical) pose.waveY = icon.state.waveTranslateX;
        else pose.waveX = icon.state.waveTranslateX;

        if (i == closestIconIndex && currentBounceIntensity > 0.0) {
            // Wave layout owns the main axis. Bounce can grow across the taskbar.
            const bool constrainedMainAxis = modeOf(icon) == AppAnimationMode::Wave || icon.fullSlotFootprint;
            if (!constrainedMainAxis || ctx.isVertical) pose.bounceScaleX = bounceScaleFactor;
            if (!constrainedMainAxis || !ctx.isVertical) pose.bounceScaleY = bounceScaleFactor;

            if (!g_settings.disableBounce && !g_settings.disableVerticalBounce) {
                if (ctx.isVertical) pose.bounceX = bounceTranslateOffset;
                else pose.bounceY = bounceTranslateOffset;
            }
        }
        ApplyIconPose(icon.transforms, pose, modeOf(icon), ctx.indicatorInsets);
    }
    return settling;
}

void ResetAllIconScales(std::vector<TaskbarIconInfo>& icons) {
    for (auto& icon : icons) {
        try {
            icon.transforms.Restore();
        } catch (const winrt::hresult_error& e) {
            Wh_Log(L"DockAnimation: Could not reset icon transforms: %s", e.message().c_str());
        }
    }
}

// Event handlers
void OnTaskbarPointerMoved(TaskbarThreadState& state, void* key,
                           DockAnimationContext& ctx, Input::PointerRoutedEventArgs const& args) {
    UpdateTaskbarEdge(ctx);
    auto frame = ctx.taskbarFrame.get();
    if (!frame || !ctx.hWnd || GetWindowThreadProcessId(ctx.hWnd, nullptr) != GetCurrentThreadId()) return;

    const double mousePos = ctx.isVertical
        ? args.GetCurrentPoint(frame).Position().Y
        : args.GetCurrentPoint(frame).Position().X;
    const auto now = std::chrono::steady_clock::now();
    if (state.activeContextKey != key) {
        if (auto previous = state.contexts.find(state.activeContextKey); previous != state.contexts.end()) {
            ResetContext(previous->second);
        }
        state.activeContextKey = key;
        state.intensity = 0.0;
        state.bounceIntensity = 0.0;
        state.bouncing = false;
        state.lastMove = now;
    }
    if (std::abs(mousePos - state.mouseX) > MOUSE_STOP_THRESHOLD) state.lastMove = now;
    state.mouseInside = true;
    state.mouseX = mousePos;

    if (!state.renderingWindow) {
        RetryPendingSubscriptions();
        if (auto pending = g_pendingSubscriptions.find(GetCurrentThreadId());
            pending != g_pendingSubscriptions.end() && std::any_of(pending->second.begin(), pending->second.end(),
                [](const auto& subscription) { return subscription.kind == PendingSubscriptionKind::Rendering; })) {
            // An old frame delegate is still alive. Leave it gated off rather
            // than registering a duplicate until revocation succeeds.
            return;
        }
        state.renderingToken = Media::CompositionTarget::Rendering(
            [](auto const&, auto const&) { OnCompositionTargetRendering(); });
        state.renderingWindow = ctx.hWnd;
        state.lastRender = now;
        state.lastMove = now;
    }
}

FrameworkElement FindChildByClassNamePartial(FrameworkElement element, PCWSTR partialName) {
    if (!element) return nullptr;
    return EnumChildElements(element, [partialName](FrameworkElement child) {
        auto className = winrt::get_class_name(child);
        return std::wstring_view(className).find(partialName) != std::wstring_view::npos;
    });
}

static FrameworkElement FindIconHost(FrameworkElement const& taskbarFrame) {
    FrameworkElement host = FindChildByClassNamePartial(taskbarFrame, L"TaskbarFrameRepeater");
    if (!host) host = FindChildByClassName(taskbarFrame, L"TaskbarFrameRepeater");
    if (!host) host = FindChildByClassName(taskbarFrame, L"TaskbarItemHost");
    return host;
}

static uint64_t Fnv1aMix(uint64_t h, uint64_t v) {
    h ^= v;
    h *= 1099511628211ULL;
    return h;
}

static HostSignature ComputeHostSignature(FrameworkElement const& host, bool isVertical) {
    HostSignature sig;
    sig.count = VisualTreeHelper::GetChildrenCount(host);
    sig.width = isVertical ? host.ActualHeight() : host.ActualWidth();

    uint64_t h = 1469598103934665603ULL;
    // Cross-axis changes alter clipping limits and the icon/indicator pivots,
    // even when the number, order, and main-axis size of buttons stay the same.
    const double crossSize = isVertical ? host.ActualWidth() : host.ActualHeight();
    h = Fnv1aMix(h, (uint64_t)(crossSize * 10.0));
    for (int i = 0; i < sig.count; i++) {
        auto child = VisualTreeHelper::GetChild(host, i).try_as<FrameworkElement>();
        if (!child) continue;
        h = Fnv1aMix(h, (uint64_t)winrt::get_abi(child));
        double size = isVertical ? child.ActualHeight() : child.ActualWidth();
        h = Fnv1aMix(h, (uint64_t)(size * 10.0));
        const double crossSize = isVertical ? child.ActualWidth() : child.ActualHeight();
        h = Fnv1aMix(h, (uint64_t)(crossSize * 10.0));
    }
    sig.orderHash = h;
    return sig;
}

static bool SigDifferent(HostSignature const& a, HostSignature const& b) {
    if (a.count != b.count) return true;
    if (std::abs(a.width - b.width) > 0.5) return true;
    if (a.orderHash != b.orderHash) return true;
    return false;
}

enum class ButtonKind {
    App,
    Start,
    Search,
    TaskView,
    Widgets,
    Weather,
    SystemOther
};

static std::wstring W(winrt::hstring const& s) {
    return std::wstring(s.c_str());
}

static std::wstring ToLower(std::wstring s) {
    for (auto& ch : s) ch = (wchar_t)towlower(ch);
    return s;
}

static std::wstring NormalizeAppId(std::wstring id) {
    id = ToLower(std::move(id));
    const auto first = id.find_first_not_of(L" \t\r\n");
    if (first == std::wstring::npos) return {};
    id.erase(0, first);
    if (id.starts_with(L"appid:")) id.erase(0, 6);
    const auto start = id.find_first_not_of(L" \t\r\n");
    if (start == std::wstring::npos) return {};
    return id.substr(start, id.find_last_not_of(L" \t\r\n") - start + 1);
}

static ButtonKind ClassifyButton(FrameworkElement const& e) {
    if (!e) return ButtonKind::SystemOther;

    std::wstring cn     = W(winrt::get_class_name(e));
    std::wstring feName = W(e.Name());
    std::wstring aid    = W(AutomationProperties::GetAutomationId(e));

    std::wstring cnL = ToLower(cn);
    std::wstring aidL = ToLower(aid);
    std::wstring feL = ToLower(feName);

    auto matches = [&](const wchar_t* s) {
        return cnL.find(s) != std::wstring::npos ||
               aidL.find(s) != std::wstring::npos ||
               feL.find(s) != std::wstring::npos;
    };

    if (cnL.ends_with(L".tasklistbutton") || aidL.starts_with(L"appid:")) {
        return ButtonKind::App;
    }

    if (matches(L"startbutton")) return ButtonKind::Start;
    if (matches(L"searchbutton")) return ButtonKind::Search;
    if (matches(L"taskviewbutton")) return ButtonKind::TaskView;
    if (matches(L"widgetsbutton") || matches(L"augmentedentrypointbutton")) return ButtonKind::Widgets;
    if (matches(L"weather")) return ButtonKind::Weather;

    return ButtonKind::SystemOther;
}


static void IncludeIconContentBounds(
    std::optional<winrt::Windows::Foundation::Rect>& content,
    winrt::Windows::Foundation::Rect bounds, bool largestOnly) {
    if (!(std::isfinite(bounds.X) && std::isfinite(bounds.Y) &&
          std::isfinite(bounds.Width) && std::isfinite(bounds.Height) &&
          bounds.Width > 0.0f && bounds.Height > 0.0f)) return;
    if (!content) {
        content = bounds;
    } else if (largestOnly) {
        if (bounds.Width * bounds.Height > content->Width * content->Height) content = bounds;
    } else {
        const float left = std::min(content->X, bounds.X);
        const float top = std::min(content->Y, bounds.Y);
        const float right = std::max(content->X + content->Width, bounds.X + bounds.Width);
        const float bottom = std::max(content->Y + content->Height, bounds.Y + bounds.Height);
        content = {left, top, right - left, bottom - top};
    }
}

static bool ShouldAnimateElement(FrameworkElement const& e) {
    const int mode = g_settings.excludeSystemButtonsMode;
    if (mode == 0) return true;

    ButtonKind k = ClassifyButton(e);

    if (mode >= 2) return k == ButtonKind::App;
    if (mode == 1) return k != ButtonKind::Start;

    return true;
}

// Read the arranged slot through its parent, never through the animated visual.
// Restoring a Composition matrix and immediately calling TransformToVisual on
// the same element can still observe its animated geometry. Feeding that back
// into the constrained wave makes a group between fixed buttons oscillate.
static winrt::Windows::Foundation::Point GetIconLayoutOrigin(
    FrameworkElement const& element, FrameworkElement const& frame) {
    auto parent = VisualTreeHelper::GetParent(element).try_as<FrameworkElement>();
    if (!parent) throw winrt::hresult_error(E_FAIL);
    const auto offset = element.ActualOffset();
    return parent.TransformToVisual(frame).TransformPoint({offset.x, offset.y});
}

static bool MeasureIconContent(DockAnimationContext& ctx, TaskbarIconInfo& info,
                        FrameworkElement const& element) {
    const double oldStart = info.footprintStart, oldEnd = info.footprintEnd;
    const float oldCrossStart = info.transforms.crossStart, oldCrossEnd = info.transforms.crossEnd;
    const bool oldFullSlot = info.fullSlotFootprint;
    info.footprintStart = 0.0;
    info.footprintEnd = 1.0;
    info.transforms.crossStart = info.transforms.crossEnd = 0.0f;
    info.fullSlotFootprint = UseFullSlotFootprint(
        winrt::get_class_name(element) == L"Taskbar.TaskListButton",
        info.elementWidth, info.transforms.crossExtent);
    if (info.elementWidth > 0.0) {
        const bool isAppButton = winrt::get_class_name(element) == L"Taskbar.TaskListButton";
        info.fullSlotFootprint = UseFullSlotFootprint(
            isAppButton, info.elementWidth, info.transforms.crossExtent);
        std::optional<winrt::Windows::Foundation::Rect> content;
        const auto findFootprint = [&](auto const& self, FrameworkElement const& parent) -> void {
            EnumChildElements(parent, [&](FrameworkElement child) {
                if (child.Visibility() != Visibility::Visible) return false;
                // Indicators, backgrounds and labels are not app glyphs.
                const auto name = child.Name();
                if (name == L"RunningIndicator" || name == L"ProgressIndicator") return false;
                const auto type = winrt::get_class_name(child);
                const std::wstring_view typeName(type);
                const bool simpleShape = typeName.ends_with(L".Shapes.Rectangle") ||
                    typeName.ends_with(L".Shapes.Ellipse") || typeName.ends_with(L".Shapes.Polygon");
                const bool glyph = child.try_as<Controls::Image>() ||
                    child.try_as<Controls::IconElement>() ||
                    (!isAppButton && (typeName.ends_with(L".AnimatedIcon") ||
                        typeName.ends_with(L".AnimatedVisualPlayer") ||
                        typeName.ends_with(L".Shapes.Path") || simpleShape ||
                        child.try_as<Controls::TextBlock>()));
                if (glyph) {
                    WatchContentSize(ctx, child);
                    const auto bounds = child.TransformToVisual(element).TransformBounds({
                        0.0f, 0.0f, static_cast<float>(child.ActualWidth()),
                        static_cast<float>(child.ActualHeight())});
                    const float start = ctx.isVertical ? bounds.Y : bounds.X;
                    const float width = ctx.isVertical ? bounds.Height : bounds.Width;
                    const float crossStart = ctx.isVertical ? bounds.X : bounds.Y;
                    const float crossSize = ctx.isVertical ? bounds.Width : bounds.Height;
                    const bool buttonBackground = simpleShape &&
                        (bounds.Width >= element.ActualWidth() * 0.9 ||
                         bounds.Height >= element.ActualHeight() * 0.9);
                    if (!buttonBackground && start >= 0.0f && start + width <= info.elementWidth &&
                        crossStart >= 0.0f && crossStart + crossSize <= info.transforms.crossExtent &&
                        (!isAppButton || width >= 12.0f)) {
                        // A system glyph can contain multiple paths or widget
                        // text blocks. Keep their union, not just one fragment.
                        IncludeIconContentBounds(content, bounds, isAppButton);
                    }
                }
                self(self, child);
                return false;
            });
        };
        findFootprint(findFootprint, element);
        if (content) {
            const float start = ctx.isVertical ? content->Y : content->X;
            const float width = ctx.isVertical ? content->Height : content->Width;
            // Application labels retain the full native slot for layout.
            if (!info.fullSlotFootprint && (!g_settings.taskbarLabelsMode || !isAppButton)) {
                info.footprintStart = start / info.elementWidth;
                info.footprintEnd = (start + width) / info.elementWidth;
            }
            info.transforms.crossStart = ctx.isVertical ? content->X : content->Y;
            info.transforms.crossEnd = info.transforms.crossStart +
                (ctx.isVertical ? content->Width : content->Height);
        }
    }

    return oldStart != info.footprintStart || oldEnd != info.footprintEnd ||
        oldCrossStart != info.transforms.crossStart || oldCrossEnd != info.transforms.crossEnd ||
        oldFullSlot != info.fullSlotFootprint;
}

static void RefreshContentGeometry(DockAnimationContext& ctx) {
    StopContentSizeWatch(ctx);
    bool changed = false;
    for (auto& icon : ctx.icons) {
        if (auto element = icon.element.get()) changed |= MeasureIconContent(ctx, icon, element);
    }
    if (changed) ctx.indicatorInsets = {};
    ctx.contentNeedsRefresh = false;
    ctx.measureIndicators = true;
    ctx.lastContentCheck = std::chrono::steady_clock::now();
}

static bool RebaseIconGeometryFast(DockAnimationContext& ctx) {
    auto frame = ctx.taskbarFrame.get();
    if (!frame) return false;

    bool changed = false;

    for (auto it = ctx.icons.begin(); it != ctx.icons.end(); ) {
        if (!it->element.get()) {
            it = ctx.icons.erase(it);
            changed = true;
        } else {
            ++it;
        }
    }

    for (auto& info : ctx.icons) {
        auto e = info.element.get();
        if (!e) continue;

        try {
            auto& transforms = info.transforms;
            // Observe another owner's writes without removing our settled pose.
            const auto current = transforms.visual.TransformMatrix();
            if (current != transforms.applied) {
                transforms.original = current;
                transforms.applied = current;
                changed = true;
            }
            const auto pt = GetIconLayoutOrigin(e, frame);
            const double width = ctx.isVertical ? e.ActualHeight() : e.ActualWidth();
            const double center = (ctx.isVertical ? pt.Y : pt.X) +
                                  (g_settings.taskbarLabelsMode ? 0.0 : width / 2.0);
            changed |= std::abs(center - info.originalCenterX) > 0.001 ||
                       std::abs(width - info.elementWidth) > 0.001;
            info.elementWidth = width;
            info.originalCenterX = center;
            SetIconPivot(transforms, e, ctx.isVertical, ctx.edge);
        } catch (...) {
        }
    }

    if (changed && ctx.icons.size() > 1) {
        std::sort(ctx.icons.begin(), ctx.icons.end(),
            [](TaskbarIconInfo const& a, TaskbarIconInfo const& b) {
                return a.originalCenterX < b.originalCenterX;
            });
    }

    return changed;
}

// Builds or refreshes the icon list and sets up transforms for animation (scale + translate).
void RefreshIconPositions(DockAnimationContext& ctx) {
    StopLayoutWatch(ctx);
    ctx.measureIndicators = true;
    ctx.needsFrame = true;
    // Preserve smoothing state across a visual tree refresh.
    std::unordered_map<void*, IconAnimState> prevStates;

    ResetAllIconScales(ctx.icons);
    for (auto& old : ctx.icons) {
        if (auto e = old.element.get()) {
            void* key = winrt::get_abi(e);
            prevStates[key] = old.state;
        }
    }

    std::vector<TaskbarIconInfo> newIcons;

    auto taskbarFrame = ctx.taskbarFrame.get();
    if (!taskbarFrame) return;
    StartLayoutWatch(ctx, taskbarFrame);

    auto IsTaskListButtonExact = [&](FrameworkElement const& e) -> bool {
        if (!e) return false;
        return winrt::get_class_name(e) == L"Taskbar.TaskListButton";
    };

    auto IsTaskListButtonPanel = [&](FrameworkElement const& e) -> bool {
        if (!e) return false;
        return winrt::get_class_name(e) == L"Taskbar.TaskListButtonPanel";
    };

    std::function<FrameworkElement(FrameworkElement)> FindFirstTaskListButton =
        [&](FrameworkElement root) -> FrameworkElement {
            if (!root) return nullptr;
            if (IsTaskListButtonExact(root)) return root;

            int c = VisualTreeHelper::GetChildrenCount(root);
            for (int i = 0; i < c; i++) {
                auto ch = VisualTreeHelper::GetChild(root, i).try_as<FrameworkElement>();
                if (!ch) continue;
                if (IsTaskListButtonExact(ch)) return ch;
                auto deep = FindFirstTaskListButton(ch);
                if (deep) return deep;
            }
            return nullptr;
        };

    // classifier node
    std::function<FrameworkElement(FrameworkElement)> FindClassifierNode =
        [&](FrameworkElement root) -> FrameworkElement {
            if (!root) return nullptr;

            auto aid = W(AutomationProperties::GetAutomationId(root));
            auto nm  = W(AutomationProperties::GetName(root));
            if (!aid.empty() || !nm.empty()) return root;

            int c = VisualTreeHelper::GetChildrenCount(root);
            for (int i = 0; i < c; i++) {
                auto ch = VisualTreeHelper::GetChild(root, i).try_as<FrameworkElement>();
                if (!ch) continue;
                auto hit = FindClassifierNode(ch);
                if (hit) return hit;
            }
            return nullptr;
        };

    // candidate in fallback: TaskListButton + TaskListButtonPanel
    auto IsFallbackCandidate = [&](FrameworkElement const& e) -> bool {
        if (!e) return false;

        if (IsTaskListButtonExact(e) || IsTaskListButtonPanel(e)) return true;

        auto cn = winrt::get_class_name(e);
        if (std::wstring_view(cn).find(L"Taskbar.") != std::wstring_view::npos) {
            auto aid = W(AutomationProperties::GetAutomationId(e));
            auto nm  = W(AutomationProperties::GetName(e));
            if (!aid.empty() || !nm.empty()) return true;
        }

        return false;
    };

    // A host child can wrap the entire tray on newer taskbar layouts.
    // Never transform that wrapper, since its transform affects every icon inside.
    auto IsTrayNode = [](FrameworkElement const& element) {
        auto className = winrt::get_class_name(element);
        return std::wstring_view(className).starts_with(L"SystemTray.") ||
               element.Name() == L"SystemTrayFrameGrid";
    };

    auto ContainsTray = [&](auto const& self, FrameworkElement const& root) -> bool {
        if (IsTrayNode(root)) return true;
        int count = VisualTreeHelper::GetChildrenCount(root);
        for (int i = 0; i < count; ++i) {
            auto child = VisualTreeHelper::GetChild(root, i).try_as<FrameworkElement>();
            if (child && self(self, child)) return true;
        }
        return false;
    };

    auto IsWidgetsButton = [](FrameworkElement const& element) {
        auto className = winrt::get_class_name(element);
        auto name = element.Name();
        return className == L"Taskbar.WidgetsButton" ||
               className == L"Taskbar.AugmentedEntryPointButton" ||
               name == L"WidgetsButton" ||
               name == L"AugmentedEntryPointButton" ||
               AutomationProperties::GetAutomationId(element) == L"WidgetsButton";
    };

    auto FindWidgets = [&](auto const& self, FrameworkElement const& root) -> FrameworkElement {
        if (IsTrayNode(root)) return nullptr;
        if (IsWidgetsButton(root) && !ContainsTray(ContainsTray, root)) {
            return root;
        }
        int count = VisualTreeHelper::GetChildrenCount(root);
        for (int i = 0; i < count; ++i) {
            auto child = VisualTreeHelper::GetChild(root, i).try_as<FrameworkElement>();
            if (child) {
                if (auto widget = self(self, child)) return widget;
            }
        }
        return nullptr;
    };

    // Setup & add element (transform + icon geometry)
    auto rules = std::atomic_load(&g_appRules);
    auto SetupAndAddElement = [&](FrameworkElement element) {
        try {
            if (!element) return;
            for (auto parent = VisualTreeHelper::GetParent(element); parent;
                 parent = VisualTreeHelper::GetParent(parent)) {
                auto ancestor = parent.try_as<FrameworkElement>();
                if (ancestor && (IsTrayNode(ancestor) ||
                                 (g_settings.disableWidgetsAnimation && IsWidgetsButton(ancestor)))) {
                    return;
                }
                if (ancestor == taskbarFrame) break;
            }
            if (ContainsTray(ContainsTray, element)) {
                if (g_settings.disableWidgetsAnimation || g_settings.excludeSystemButtonsMode >= 2) return;
                element = FindWidgets(FindWidgets, element);
                if (!element) return;
            }
            if (g_settings.disableWidgetsAnimation && FindWidgets(FindWidgets, element)) return;

            IconTransforms transforms;
            transforms.visual = Hosting::ElementCompositionPreview::GetElementVisual(element);
            if (!transforms.visual) return;
            transforms.original = transforms.visual.TransformMatrix();
            transforms.applied = transforms.original;
            SetIconPivot(transforms, element, ctx.isVertical, ctx.edge);

            const auto point = GetIconLayoutOrigin(element, taskbarFrame);

            TaskbarIconInfo info;
            info.element = element;
            info.transforms = std::move(transforms);
            if (IsTaskListButtonExact(element)) {
                info.transforms.button = element;
                const auto collectIndicators = [&](auto const& self, FrameworkElement const& parent) -> void {
                    EnumChildElements(parent, [&](FrameworkElement child) {
                        const auto name = child.Name();
                        if (name == L"RunningIndicator" || name == L"ProgressIndicator") {
                            IndicatorTransforms indicator;
                            indicator.element = child;
                            indicator.visual = Hosting::ElementCompositionPreview::GetElementVisual(child);
                            if (indicator.visual) {
                                indicator.original = indicator.visual.TransformMatrix();
                                indicator.applied = indicator.original;
                                info.transforms.indicators.push_back(std::move(indicator));
                                WatchIndicatorVisibility(ctx, child);
                            }
                        } else {
                            self(self, child);
                        }
                        return false;
                    });
                };
                collectIndicators(collectIndicators, element);
            }
            if (rules && !rules->empty() && IsTaskListButtonExact(element)) {
                auto matchId = [&](FrameworkElement const& node) {
                    auto rawId = W(AutomationProperties::GetAutomationId(node));
                    auto id = NormalizeAppId(rawId);
                    auto match = rules->find(id);
                    if (match == rules->end()) return false;
                    info.rule = match->second;
                    return true;
                };

                bool matched = false;
                for (auto node = element; node && node != taskbarFrame;
                     node = VisualTreeHelper::GetParent(node).try_as<FrameworkElement>()) {
                    if (matchId(node)) {
                        matched = true;
                        break;
                    }
                }
                if (!matched) {
                    auto matchChild = [&](auto const& self, FrameworkElement const& parent) -> bool {
                        const int count = VisualTreeHelper::GetChildrenCount(parent);
                        for (int i = 0; i < count; ++i) {
                            auto child = VisualTreeHelper::GetChild(parent, i).try_as<FrameworkElement>();
                            if (child && (matchId(child) || self(self, child))) return true;
                        }
                        return false;
                    };
                    matchChild(matchChild, element);
                }
            }
            info.elementWidth = ctx.isVertical ? element.ActualHeight() : element.ActualWidth();

            MeasureIconContent(ctx, info, element);

            info.originalCenterX = (ctx.isVertical ? point.Y : point.X) +
                                   (g_settings.taskbarLabelsMode ? 0.0 : info.elementWidth / 2.0);

            void* key = winrt::get_abi(element);

            if (auto it = prevStates.find(key); it != prevStates.end()) {
                info.state = it->second;
            }

            newIcons.push_back(info);
        } catch (winrt::hresult_error const& e) {
            Wh_Log(L"DockAnimation: HRESULT error in SetupAndAddElement: %s", e.message().c_str());
        }
    };

    // SMART host find (structure-based)
    auto FindSmartHost = [&]() -> FrameworkElement {
        std::vector<FrameworkElement> nodes;
        nodes.reserve(512);

        std::vector<FrameworkElement> stack;
        stack.reserve(512);
        stack.push_back(taskbarFrame);

        while (!stack.empty()) {
            auto cur = stack.back();
            stack.pop_back();
            if (!cur) continue;

            nodes.push_back(cur);

            int c = VisualTreeHelper::GetChildrenCount(cur);
            for (int i = 0; i < c; i++) {
                auto ch = VisualTreeHelper::GetChild(cur, i).try_as<FrameworkElement>();
                if (ch) stack.push_back(ch);
            }
        }

        std::function<bool(FrameworkElement,int)> SubtreeHasIconLike =
            [&](FrameworkElement root, int depth) -> bool {
                if (!root || depth <= 0) return false;
                if (IsTaskListButtonExact(root) || IsTaskListButtonPanel(root)) return true;

                int c = VisualTreeHelper::GetChildrenCount(root);
                for (int i = 0; i < c; i++) {
                    auto ch = VisualTreeHelper::GetChild(root, i).try_as<FrameworkElement>();
                    if (!ch) continue;
                    if (SubtreeHasIconLike(ch, depth - 1)) return true;
                }
                return false;
            };

        FrameworkElement best = nullptr;
        int bestHits = 0;
        double bestWidth = 0.0;

        for (auto const& n : nodes) {
            int c = VisualTreeHelper::GetChildrenCount(n);
            if (c < 3 || c > 120) continue;

            int hits = 0;
            for (int i = 0; i < c; i++) {
                auto ch = VisualTreeHelper::GetChild(n, i).try_as<FrameworkElement>();
                if (!ch) continue;
                if (SubtreeHasIconLike(ch, 5)) hits++;
            }

            if (hits >= 3) {
                double w = (double)n.ActualWidth();
                if (hits > bestHits || (hits == bestHits && w > bestWidth)) {
                    best = n;
                    bestHits = hits;
                    bestWidth = w;
                }
            }
        }

        return best;
    };

    // host selection
    auto host = ctx.iconHost.get();
    if (!host) {
        host = FindSmartHost();
        if (host) ctx.iconHost = host;
    }

    try {
        if (host) {
            // MAIN: enumerate host children
            int count = VisualTreeHelper::GetChildrenCount(host);
            for (int i = 0; i < count; i++) {
                auto child = VisualTreeHelper::GetChild(host, i).try_as<FrameworkElement>();
                if (!child) continue;

                FrameworkElement classifier = FindClassifierNode(child);
                FrameworkElement base = classifier ? classifier : child;

                bool animate = (g_settings.excludeSystemButtonsMode == 0)
                    ? true
                    : ShouldAnimateElement(base);

                // target: prefer TaskListButton inside, else child
                FrameworkElement target = FindFirstTaskListButton(child);
                if (!target) target = child;

                if (!animate) continue;

                SetupAndAddElement(target);
            }

            ctx.lastSig = ComputeHostSignature(host, ctx.isVertical);
        } else {
            // FALLBACK: recurse and include TaskListButtonPanel too
            std::function<void(FrameworkElement)> recurse = [&](FrameworkElement element) {
                if (!element) return;

                if (IsFallbackCandidate(element)) {
                    FrameworkElement classifier = FindClassifierNode(element);
                    FrameworkElement base = classifier ? classifier : element;

                    bool animate = (g_settings.excludeSystemButtonsMode == 0)
                        ? true
                        : ShouldAnimateElement(base);

                    FrameworkElement target = FindFirstTaskListButton(element);
                    if (!target) target = element;

                    if (animate) SetupAndAddElement(target);
                }

                int c = VisualTreeHelper::GetChildrenCount(element);
                for (int i = 0; i < c; i++) {
                    auto ch = VisualTreeHelper::GetChild(element, i).try_as<FrameworkElement>();
                    if (ch) recurse(ch);
                }
            };

            recurse(taskbarFrame);
        }

        std::sort(newIcons.begin(), newIcons.end(),
            [](TaskbarIconInfo const& a, TaskbarIconInfo const& b) {
                return a.originalCenterX < b.originalCenterX;
            });

        ctx.icons = std::move(newIcons);
        ctx.indicatorInsets = {};
        ctx.lastGeometryCheck = std::chrono::steady_clock::now();
        ctx.lastContentCheck = ctx.lastGeometryCheck;
        ctx.contentNeedsRefresh = false;

    } catch (winrt::hresult_error const& e) {
        Wh_Log(L"DockAnimation: HRESULT error during icon search: %s", e.message().c_str());
    }
}

// Main animation loop (pulse)
void OnCompositionTargetRendering() {
    std::lock_guard lock(g_animationMutex);
    if (g_unloading) return;
    auto thread = g_taskbarThreads.find(GetCurrentThreadId());
    if (thread == g_taskbarThreads.end() || !thread->second.renderingWindow) return;
    auto& state = thread->second;
    try {
        auto now = std::chrono::steady_clock::now();

        double deltaTime = std::chrono::duration_cast<std::chrono::milliseconds>(
                                now - state.lastRender)
                                .count();
        state.lastRender = now;

        double dtSec = std::max(0.0, deltaTime) / 1000.0;

        double intensityChange = deltaTime / g_settings.focusDuration;
        const double previousIntensity = state.intensity;
        double currentIntensity = previousIntensity;

        if (state.mouseInside) {
            // FocusIn
            currentIntensity = std::min(1.0, currentIntensity + intensityChange);
        } else {
            // FocusOut
            currentIntensity = std::max(0.0, currentIntensity - intensityChange);
        }

        state.intensity = currentIntensity;

        auto it = state.contexts.find(state.activeContextKey);
        if (it == state.contexts.end()) {
            StopRendering(state);
            return;
        }
        auto& ctx = it->second;

        if (!state.mouseInside && currentIntensity <= 0.0) {
            ResetContext(ctx);
            StopRendering(state);
            state.activeContextKey = nullptr;
            state.mouseX = -1.0;
            state.bouncing = false;
            state.bounceIntensity = 0.0;
            return;
        }

        if (state.settingsRevision != g_settingsRevision) {
            ResetContext(ctx);
            state.settingsRevision = g_settingsRevision;
            state.bouncing = false;
            state.bounceIntensity = 0.0;
            state.lastMove = now;
        }

        if (!ctx.isInitialized) {
            RefreshIconPositions(ctx);
            ctx.isInitialized = true;
            ctx.lastDirtyCheck = now;
        }

        if (ctx.layoutSignal &&
            ctx.layoutSignal->contentDirty.exchange(false, std::memory_order_relaxed)) {
            ctx.contentNeedsRefresh = true;
        }
        if (ctx.layoutSignal &&
            ctx.layoutSignal->indicatorsDirty.exchange(false, std::memory_order_relaxed)) {
            ctx.measureIndicators = true;
            ctx.needsFrame = true;
        }

        // Keep the cheap structure poll; only remeasure stable geometry when
        // layout changed or the one-second fallback is due.
        if (state.mouseInside) {
            auto sinceCheck = std::chrono::duration_cast<std::chrono::milliseconds>(
                now - ctx.lastDirtyCheck).count();

            if (sinceCheck > 120) {
                ctx.lastDirtyCheck = now;

                auto frame = ctx.taskbarFrame.get();
                if (frame) {
                    UpdateTaskbarEdge(ctx);
                    if (!ctx.isInitialized) {
                        RefreshIconPositions(ctx);
                        ctx.isInitialized = true;
                    }

                    auto host = ctx.iconHost.get();
                    if (!host) {
                        host = FindIconHost(frame);
                        if (host) ctx.iconHost = host;
                    }

                    if (host) {
                        HostSignature sig = ComputeHostSignature(host, ctx.isVertical);

                        if (ctx.icons.empty() || SigDifferent(sig, ctx.lastSig)) {
                            RefreshIconPositions(ctx);
                        } else {
                            const bool dirty = ctx.layoutSignal &&
                                ctx.layoutSignal->geometryDirty.exchange(false, std::memory_order_relaxed);
                            const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
                                now - ctx.lastGeometryCheck);
                            if (ShouldRefreshGeometry(ctx.layoutSubscribed, dirty, elapsed)) {
                                RebaseIconGeometryFast(ctx);
                                if (ctx.contentNeedsRefresh || now - ctx.lastContentCheck >= std::chrono::seconds(1)) {
                                    RefreshContentGeometry(ctx);
                                }
                                ctx.measureIndicators = true;
                                ctx.needsFrame = true;
                                ctx.lastGeometryCheck = now;
                            }
                        }

                        ctx.lastSig = sig;
                    } else if (ctx.icons.empty()) {
                        RefreshIconPositions(ctx);
                    }
                }
            }
        }

        if (ctx.icons.empty()) return;

        if (g_settings.disableBounce) {
            state.bouncing = false;
        } else {
            auto elapsedSinceMove =
                std::chrono::duration_cast<std::chrono::milliseconds>(
                    now - state.lastMove)
                    .count();

            if (state.mouseInside && elapsedSinceMove > g_settings.bounceDelay) {
                if (!state.bouncing) {
                    state.bouncing = true;
                    state.bounceStart = now;
                }
            } else {
                state.bouncing = false;
            }
        }

        double targetBounceIntensity = state.bouncing ? 1.0 : 0.0;
        double bounceFadeDuration = g_settings.focusDuration / 1000.0;
        double bounceIntensityChange = dtSec / bounceFadeDuration;
        const double previousBounceIntensity = state.bounceIntensity;
        double currentBounceIntensity = previousBounceIntensity;
        if (targetBounceIntensity > currentBounceIntensity) {
            currentBounceIntensity = std::min(targetBounceIntensity, currentBounceIntensity + bounceIntensityChange);
        } else {
            currentBounceIntensity = std::max(targetBounceIntensity, currentBounceIntensity - bounceIntensityChange);
        }
        state.bounceIntensity = currentBounceIntensity;

        double mouseX = state.mouseX;
        if (mouseX == -1.0) mouseX = 0.0;

        // The callback still checks for geometry changes and delayed bounce.
        // A settled hover needs no layout solve or transform writes.
        if (ctx.needsFrame || mouseX != ctx.lastLayoutMouse || ctx.edge != ctx.lastLayoutEdge ||
            currentIntensity != previousIntensity ||
            currentBounceIntensity > 0.0 || previousBounceIntensity > 0.0) {
            ctx.needsFrame = ApplyAnimation(mouseX, ctx, currentIntensity, dtSec, state);
            ctx.lastLayoutMouse = mouseX;
            ctx.lastLayoutEdge = ctx.edge;
        }
    } catch (...) {
        if (auto it = state.contexts.find(state.activeContextKey); it != state.contexts.end()) {
            ResetContext(it->second);
        }
        try {
            StopRendering(state);
        } catch (const winrt::hresult_error& e) {
            Wh_Log(L"DockAnimation: Could not stop rendering after an error: %s", e.message().c_str());
        }
    }
}

// Hooking
// Pointer event hooks (new approach: activates mod immediately)
using TaskbarFrame_OnPointerMoved_t = int(WINAPI*)(void* pThis, void* pArgs);
TaskbarFrame_OnPointerMoved_t TaskbarFrame_OnPointerMoved_Original;

int WINAPI TaskbarFrame_OnPointerMoved_Hook(void* pThis, void* pArgs) {
    auto original = [=]() {
        return TaskbarFrame_OnPointerMoved_Original(pThis, pArgs);
    };
    if (g_unloading.load()) return original();
    FrameworkElement element = nullptr;
    ((IUnknown*)pThis)->QueryInterface(winrt::guid_of<FrameworkElement>(), winrt::put_abi(element));
    if (!element)
        return original();
    auto className = winrt::get_class_name(element);
    if (className != L"Taskbar.TaskbarFrame")
        return original();
    Input::PointerRoutedEventArgs args = nullptr;
    ((IUnknown*)pArgs)->QueryInterface(winrt::guid_of<Input::PointerRoutedEventArgs>(), winrt::put_abi(args));
    if (!args)
        return original();
    {
        std::lock_guard lock(g_animationMutex);
        if (!g_unloading) {
            try {
                auto& state = g_taskbarThreads[GetCurrentThreadId()];
                auto& ctx = state.contexts[pThis];
                if (ctx.taskbarFrame.get() != element) {
                    ResetContext(ctx);
                    ctx = {};
                    ctx.taskbarFrame = element;
                    ctx.hWnd = GetCurrentThreadTrayWindow();
                }
                OnTaskbarPointerMoved(state, pThis, ctx, args);
            } catch (const winrt::hresult_error& e) {
                Wh_Log(L"DockAnimation: Pointer move failed: %s", e.message().c_str());
            }
        }
    }
    return original();
}

using TaskbarFrame_OnPointerExited_t = int(WINAPI*)(void* pThis, void* pArgs);
TaskbarFrame_OnPointerExited_t TaskbarFrame_OnPointerExited_Original;

int WINAPI TaskbarFrame_OnPointerExited_Hook(void* pThis, void* pArgs) {
    auto original = [=]() {
        return TaskbarFrame_OnPointerExited_Original(pThis, pArgs);
    };
    if (g_unloading.load()) return original();
    FrameworkElement element = nullptr;
    ((IUnknown*)pThis)->QueryInterface(winrt::guid_of<FrameworkElement>(), winrt::put_abi(element));
    if (!element)
        return original();
    auto className = winrt::get_class_name(element);
    if (className != L"Taskbar.TaskbarFrame")
        return original();
    {
        std::lock_guard lock(g_animationMutex);
        if (!g_unloading) {
            auto thread = g_taskbarThreads.find(GetCurrentThreadId());
            if (thread != g_taskbarThreads.end() && thread->second.activeContextKey == pThis) {
                thread->second.mouseInside = false;
                thread->second.bouncing = false;
            }
        }
    }
    return original();
}

template <typename... Args>
int ReadChoice(PCWSTR key, Args... args) {
    WindhawkUtils::StringSetting setting(Wh_GetStringSetting(key, args...));
    std::wstring_view value(setting.get());
    // Existing installations store the same option IDs as integers.
    if (value.empty()) return Wh_GetIntSetting(key, args...);
    if (value == L"cosine" || value == L"all") return 0;
    if (value == L"linear" || value == L"exclude_start") return 1;
    if (value == L"exponential" || value == L"apps_only") return 2;
    if (value.size() == 1 && value[0] >= L'0' && value[0] <= L'2') {
        return value[0] - L'0';
    }
    return -1;
}

void LoadSettings() {
    WindhawkUtils::StringSetting position(Wh_GetStringSetting(L"TaskbarPosition"));
    g_settings.taskbarPosition = ParseTaskbarPosition(position.get());
    int rawScale = Wh_GetIntSetting(L"MaxScale");

    if (rawScale < 101) {
        rawScale = 101;
    } else if (rawScale > 220) {
        rawScale = 220;
    }

    g_settings.animationType = ReadChoice(L"AnimationType");
    g_settings.maxScale = (double)rawScale / 100.0;

    g_settings.effectRadius = Wh_GetIntSetting(L"EffectRadius");
    if (g_settings.effectRadius <= 0) g_settings.effectRadius = 100;

    g_settings.spacingFactor = (double)Wh_GetIntSetting(L"SpacingFactor") / 100.0;
    if (g_settings.spacingFactor < 0.0) g_settings.spacingFactor = 0.5;

    g_settings.bounceDelay = Wh_GetIntSetting(L"BounceDelay");
    if (g_settings.bounceDelay < 0) g_settings.bounceDelay = 500;

    g_settings.focusDuration = (double)Wh_GetIntSetting(L"FocusDuration");
    if (g_settings.focusDuration <= 0) g_settings.focusDuration = 150.0;

    g_settings.disableVerticalBounce = (bool)Wh_GetIntSetting(L"DisableVerticalBounce");
    g_settings.taskbarLabelsMode = (bool)Wh_GetIntSetting(L"TaskbarLabelsMode");
    g_settings.excludeSystemButtonsMode = ReadChoice(L"ExcludeSystemButtonsMode");
    g_settings.disableWidgetsAnimation = Wh_GetIntSetting(L"DisableWidgetsAnimation") != 0;
    g_settings.hoveredIconOnly = Wh_GetIntSetting(L"HoveredIconOnly") != 0;

    g_settings.lerpSpeed = (double)Wh_GetIntSetting(L"LerpSpeed");
    if (g_settings.lerpSpeed < 0) g_settings.lerpSpeed = 0;
    if (g_settings.lerpSpeed > 60) g_settings.lerpSpeed = 60;

    g_settings.disableBounce = (bool)Wh_GetIntSetting(L"DisableBounce");

    auto rules = std::make_shared<AppRuleMap>();
    for (int index = 0; index < 256; ++index) {
        WindhawkUtils::StringSetting configuredId(Wh_GetStringSetting(L"AppRules[%d].AppId", index));
        auto id = NormalizeAppId(configuredId.get());
        if (id.empty()) continue;

        AppAnimationMode mode;
        switch (ReadChoice(L"AppRules[%d].Mode", index)) {
            case 0: mode = AppAnimationMode::Wave; break;
            case 1: mode = AppAnimationMode::Single; break;
            case 2: mode = AppAnimationMode::Off; break;
            default: continue;
        }
        const int scale = Wh_GetIntSetting(L"AppRules[%d].MaxScale", index);
        (*rules)[id] = {mode, scale >= 101 && scale <= 220 ? scale / 100.0 : 0.0};
    }
    std::atomic_store(&g_appRules, std::shared_ptr<const AppRuleMap>(std::move(rules)));

    Wh_Log(L"DockAnimation: Settings loaded.");
}

HMODULE GetTaskbarViewModuleHandle() {
    HMODULE module = GetModuleHandle(L"Taskbar.View.dll");
    if (!module) module = GetModuleHandle(L"ExplorerExtensions.dll");
    return module;
}

bool HookTaskbarViewDllSymbols(HMODULE module) {
    // Taskbar.View.dll, ExplorerExtensions.dll
    WindhawkUtils::SYMBOL_HOOK taskbarViewHooks[] = {
        {
            {
                LR"(public: virtual int __cdecl winrt::impl::produce<struct winrt::Taskbar::implementation::TaskbarFrame,struct winrt::Windows::UI::Xaml::Controls::IControlOverrides>::OnPointerMoved(void *))"
            },
            &TaskbarFrame_OnPointerMoved_Original,
            TaskbarFrame_OnPointerMoved_Hook,
        },
        {
            {
                LR"(public: virtual int __cdecl winrt::impl::produce<struct winrt::Taskbar::implementation::TaskbarFrame,struct winrt::Windows::UI::Xaml::Controls::IControlOverrides>::OnPointerExited(void *))"
            },
            &TaskbarFrame_OnPointerExited_Original,
            TaskbarFrame_OnPointerExited_Hook,
        },
    };
    if (!HookSymbols(module, taskbarViewHooks, ARRAYSIZE(taskbarViewHooks))) {
        Wh_Log(L"DockAnimation: HookSymbols failed.");
        return false;
    }
    Wh_Log(L"DockAnimation: HookSymbols succeeded (Pointer events only).");
    return true;
}

using LoadLibraryExW_t = decltype(&LoadLibraryExW);
LoadLibraryExW_t LoadLibraryExW_Original;

// Lazy hook path (if Taskbar.View.dll loads later)
HMODULE WINAPI LoadLibraryExW_Hook(LPCWSTR lpLibFileName, HANDLE hFile, DWORD dwFlags) {
    HMODULE module = LoadLibraryExW_Original(lpLibFileName, hFile, dwFlags);
    if (!module) return module;

    if (!g_taskbarViewDllLoaded && GetTaskbarViewModuleHandle() == module) {
        if (!g_taskbarViewDllLoaded.exchange(true)) {
            Wh_Log(L"DockAnimation: Taskbar.View.dll loaded, hooking symbols...");
            if (HookTaskbarViewDllSymbols(module)) {
                Wh_ApplyHookOperations();
                Wh_Log(L"DockAnimation: Hooks applied (slow path).");
            }
        }
    }
    return module;
}

// Windhawk entry points
BOOL Wh_ModInit() {
    // A DLL retained after failed cleanup still owns old delegate code. Do
    // not reuse its globals for a new activation in the same Explorer process.
    if (g_unloading.load()) {
        Wh_Log(L"DockAnimation: Previous callback cleanup was incomplete; restart Explorer before enabling again.");
        return FALSE;
    }
    Wh_Log(L"DockAnimation: Wh_ModInit");
    LoadSettings();

    if (HMODULE taskbarViewModule = GetTaskbarViewModuleHandle()) {
        g_taskbarViewDllLoaded = true;
        if (!HookTaskbarViewDllSymbols(taskbarViewModule)) return FALSE;
    } else {
        HMODULE kernelBaseModule = GetModuleHandle(L"kernelbase.dll");
        auto pKernelBaseLibraryExW =
            (decltype(&LoadLibraryExW))GetProcAddress(kernelBaseModule, "LoadLibraryExW");
        WindhawkUtils::SetFunctionHook(
            pKernelBaseLibraryExW,
            LoadLibraryExW_Hook,
            &LoadLibraryExW_Original);
    }
    return AcquireCallbackModuleReference() ? TRUE : FALSE;
}

void Wh_ModUninit() {
    ReleaseCallbackModuleReference();
}

typedef void (*RunFromWindowThreadProc_t)(PVOID);

bool RunFromWindowThread(HWND hWnd,
                         RunFromWindowThreadProc_t proc,
                         PVOID procParam) {
    static const UINT runFromWindowThreadRegisteredMsg =
        RegisterWindowMessage(L"Windhawk_RunFromWindowThread_" WH_MOD_ID);
    struct RUN_FROM_WINDOW_THREAD_PARAM {
        RunFromWindowThreadProc_t proc;
        PVOID procParam;
        bool called = false;
    };

    DWORD processId = 0;
    DWORD dwThreadId = GetWindowThreadProcessId(hWnd, &processId);
    if (!dwThreadId || processId != GetCurrentProcessId()) {
        return false;
    }

    if (dwThreadId == GetCurrentThreadId()) {
        proc(procParam);
        return true;
    }

    HHOOK hook = SetWindowsHookEx(
        WH_CALLWNDPROC,
        [](int nCode, WPARAM wParam, LPARAM lParam) -> LRESULT {
            if (nCode == HC_ACTION) {
                const CWPSTRUCT* cwp = (const CWPSTRUCT*)lParam;
                if (cwp->message == runFromWindowThreadRegisteredMsg) {
                    RUN_FROM_WINDOW_THREAD_PARAM* param =
                        (RUN_FROM_WINDOW_THREAD_PARAM*)cwp->lParam;
                    param->called = true;
                    param->proc(param->procParam);
                }
            }
            return CallNextHookEx(nullptr, nCode, wParam, lParam);
        },
        nullptr, dwThreadId);
    if (!hook) {
        return false;
    }

    RUN_FROM_WINDOW_THREAD_PARAM param;
    param.proc = proc;
    param.procParam = procParam;
    SendMessage(hWnd, runFromWindowThreadRegisteredMsg, 0, (LPARAM)&param);

    UnhookWindowsHookEx(hook);
    return param.called;
}

void Wh_ModBeforeUninit() {
    // Closing the gate under the callback lock waits for any in-flight event
    // registration. The thread-state entries stay alive during UI cleanup.
    {
        std::lock_guard lock(g_animationMutex);
        g_unloading = true;
    }

    for (auto it = g_taskbarThreads.begin(); it != g_taskbarThreads.end();) {
        auto& [threadId, state] = *it;
        HWND owner = state.renderingWindow;
        if (!owner || GetWindowThreadProcessId(owner, nullptr) != threadId) {
            owner = nullptr;
            EnumThreadWindows(threadId, [](HWND window, LPARAM param) -> BOOL {
                *reinterpret_cast<HWND*>(param) = window;
                return FALSE;
            }, reinterpret_cast<LPARAM>(&owner));
        }
        if (!owner || !RunFromWindowThread(owner, [](PVOID param) {
                auto& state = *static_cast<TaskbarThreadState*>(param);
                try {
                    StopRendering(state);
                } catch (const winrt::hresult_error& e) {
                    Wh_Log(L"DockAnimation: Could not unsubscribe from rendering: %s", e.message().c_str());
                }
                for (auto& [key, ctx] : state.contexts) {
                    ResetContext(ctx);
                }
                state.contexts.clear();
            }, &state)) {
            // Keep unreachable state alive rather than release its visuals
            // from the Windhawk engine thread.
            PreserveCallbackModule();
            Wh_Log(L"DockAnimation: Could not reach taskbar thread %lu for cleanup.", threadId);
            ++it;
        } else {
            it = g_taskbarThreads.erase(it);
        }
    }

    g_taskbarViewDllLoaded = false;
}

void Wh_ModSettingsChanged() {
    std::lock_guard lock(g_animationMutex);
    if (g_unloading) return;
    LoadSettings();
    ++g_settingsRevision;
}
