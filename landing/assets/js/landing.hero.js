"use strict";

/**
 * Hero scroll-driven frame sequence.
 * Memutar 64 frame (.jpg) di atas <canvas> mengikuti progress scroll,
 * dengan cross-fade antar-frame agar transisi sehalus video.
 * Dipanggil dari initLanding() hanya saat prefers-reduced-motion = false.
 */
function initHeroFrameParallax() {
  const hero = document.querySelector(".hero");
  const canvas = document.getElementById("heroFrameCanvas");
  if (!hero || !canvas) return;

  const context = canvas.getContext("2d", { alpha: false });
  if (!context) return;

  // 64 frame berurutan (001..064). Lebih banyak frame + cross-fade antar frame
  // di bawah = animasi sangat halus dan terkesan premium.
  const TOTAL_FRAMES = 64;
  const frameNumbers = Array.from({ length: TOTAL_FRAMES }, (_, i) => i + 1);
  const frameSources = frameNumbers.map((number) => `assets/img/hero-frames/frame_${String(number).padStart(3, "0")}.jpg`);
  const frames = new Array(frameSources.length);
  let targetProgress = 0;
  let currentProgress = 0;
  let rafId = 0;
  let lastFrameKey = -1;
  let viewportWidth = 0;
  let viewportHeight = 0;

  const isMobile = window.innerWidth <= 560;

  function resizeCanvas() {
    const rect = canvas.getBoundingClientRect();
    // Cap DPR lower on mobile for better performance
    const maxDpr = isMobile ? 1 : 1.5;
    const dpr = Math.min(window.devicePixelRatio || 1, maxDpr);
    viewportWidth = Math.max(1, Math.round(rect.width * dpr));
    viewportHeight = Math.max(1, Math.round(rect.height * dpr));
    if (canvas.width !== viewportWidth || canvas.height !== viewportHeight) {
      canvas.width = viewportWidth;
      canvas.height = viewportHeight;
      lastFrameKey = -1;
      drawProgress(currentProgress, true);
    }
  }

  function drawCover(image) {
    const imageRatio = image.naturalWidth / image.naturalHeight;
    const canvasRatio = viewportWidth / viewportHeight;
    let drawWidth;
    let drawHeight;
    let offsetX;
    let offsetY;

    if (imageRatio > canvasRatio) {
      drawHeight = viewportHeight;
      drawWidth = drawHeight * imageRatio;
      offsetX = (viewportWidth - drawWidth) / 2;
      offsetY = 0;
    } else {
      drawWidth = viewportWidth;
      drawHeight = drawWidth / imageRatio;
      offsetX = 0;
      offsetY = (viewportHeight - drawHeight) / 2;
    }

    context.drawImage(image, offsetX, offsetY, drawWidth, drawHeight);
  }

  function nearestLoadedFrame(index) {
    if (frames[index] && frames[index].complete) return frames[index];
    for (let distance = 1; distance < frames.length; distance += 1) {
      const before = frames[index - distance];
      const after = frames[index + distance];
      if (before && before.complete) return before;
      if (after && after.complete) return after;
    }
    return null;
  }

  function drawProgress(progress, force) {
    const maxIndex = frames.length - 1;
    const exact = Math.max(0, Math.min(maxIndex, progress * maxIndex));
    const baseIndex = Math.floor(exact);
    const frac = exact - baseIndex;
    const nextIndex = Math.min(maxIndex, baseIndex + 1);

    // Kunci resolusi-halus (1/120 frame) supaya redraw terjadi mulus saat glide,
    // tanpa menggambar ulang berlebihan ketika nilainya tak berubah berarti.
    const key = Math.round(exact * 120);
    if (!force && key === lastFrameKey) return;

    const baseFrame = nearestLoadedFrame(baseIndex);
    if (!baseFrame || !baseFrame.naturalWidth) return;

    context.fillStyle = "#F8FAFC";
    context.fillRect(0, 0, viewportWidth, viewportHeight);
    context.globalAlpha = 1;
    drawCover(baseFrame);

    // Cross-fade ke frame berikutnya untuk transisi sehalus video.
    if (frac > 0.001 && nextIndex !== baseIndex) {
      const nextFrame = frames[nextIndex];
      if (nextFrame && nextFrame.complete && nextFrame.naturalWidth) {
        context.globalAlpha = frac;
        drawCover(nextFrame);
        context.globalAlpha = 1;
      }
    }

    lastFrameKey = key;
    hero.classList.add("has-canvas");
  }

  function animate() {
    const difference = targetProgress - currentProgress;
    currentProgress += difference * 0.17;
    if (Math.abs(difference) < 0.0005) currentProgress = targetProgress;

    drawProgress(currentProgress, false);

    if (Math.abs(targetProgress - currentProgress) > 0.0005) rafId = requestAnimationFrame(animate);
    else rafId = 0;
  }

  function updateFromScroll() {
    const start = hero.offsetTop;
    const parallaxDistance = hero.offsetHeight - (window.innerHeight * 2);
    const distance = Math.max(1, parallaxDistance);
    targetProgress = Math.max(0, Math.min(1, (window.scrollY - start) / distance));
    if (!rafId) rafId = requestAnimationFrame(animate);
  }

  function loadFrame(index) {
    if (frames[index]) return;
    const image = new Image();
    image.decoding = "async";
    frames[index] = image;
    image.src = frameSources[index];
    image.onload = () => {
      if (index === 0 || index === Math.round(currentProgress * (frames.length - 1))) drawProgress(currentProgress, true);
    };
  }

  resizeCanvas();
  // Load fewer initial frames on mobile for faster first paint
  const initialFrames = isMobile ? 6 : 12;
  for (let i = 0; i < initialFrames; i += 1) loadFrame(i);
  const loadRemaining = () => frameSources.forEach((_, index) => loadFrame(index));
  if ("requestIdleCallback" in window) window.requestIdleCallback(loadRemaining, { timeout: isMobile ? 2000 : 1200 });
  else window.setTimeout(loadRemaining, 200);

  window.addEventListener("scroll", updateFromScroll, { passive: true });
  window.addEventListener("resize", () => {
    resizeCanvas();
    updateFromScroll();
  }, { passive: true });

  updateFromScroll();
}
