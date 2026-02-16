/**
 * QR Code Renderer — client-side wrapper around qr-code-styling.
 *
 * Usage:
 *   const renderer = new QRCodeRenderer(containerEl, {
 *     data: "https://…",
 *     fillColor: "#000000",
 *     fillColorSecondary: "#000000",
 *     backgroundColor: "#FFFFFF",
 *     style: "square",
 *     colorMask: "solid",
 *     logoUrl: "/media/qr_logos/…",
 *     badgeUrl: "/static/img/qr-badges/logo-filtering.png",
 *     showBadge: true,
 *   });
 *   renderer.render();
 *   renderer.download("my-qr-code");
 */
class QRCodeRenderer {
  static STYLE_MAP = {
    square: "square",
    rounded: "extra-rounded",
    circle: "dots",
  };

  static SIZE = 400;

  constructor(container, options) {
    this.container = container;
    this.options = options;
    this.qrCode = null;
    this._renderVersion = 0;
  }

  _buildGradient(colorMask, fillColor, fillColorSecondary) {
    if (colorMask === "solid") {
      return undefined;
    }
    const colorStops = [
      { offset: 0, color: fillColorSecondary },
      { offset: 1, color: fillColor },
    ];
    if (colorMask === "round_radial" || colorMask === "square_radial") {
      return { type: "radial", colorStops };
    }
    if (colorMask === "horizontal_gradiant") {
      return { type: "linear", rotation: 0, colorStops };
    }
    if (colorMask === "vertical_gradiant") {
      return { type: "linear", rotation: Math.PI / 2, colorStops };
    }
    return undefined;
  }

  _buildQROptions() {
    const {
      data,
      fillColor = "#000000",
      fillColorSecondary = "#000000",
      backgroundColor = "#FFFFFF",
      style = "square",
      colorMask = "solid",
      logoUrl,
    } = this.options;

    const dotType = QRCodeRenderer.STYLE_MAP[style] || "square";
    const gradient = this._buildGradient(colorMask, fillColor, fillColorSecondary);

    const opts = {
      width: QRCodeRenderer.SIZE,
      height: QRCodeRenderer.SIZE,
      type: "canvas",
      data,
      margin: 8,
      qrOptions: {
        errorCorrectionLevel: "H",
      },
      dotsOptions: {
        type: dotType,
        ...(gradient ? { gradient } : { color: fillColor }),
      },
      backgroundOptions: {
        color: backgroundColor,
      },
      cornersSquareOptions: {
        type: "square",
        ...(gradient ? { gradient } : { color: fillColor }),
      },
      cornersDotOptions: {
        type: "square",
        ...(gradient ? { gradient } : { color: fillColor }),
      },
    };

    if (logoUrl) {
      opts.image = logoUrl;
      opts.imageOptions = {
        crossOrigin: "anonymous",
        hideBackgroundDots: true,
        imageSize: 0.35,
        margin: 8,
      };
    }

    return opts;
  }

  render() {
    while (this.container.firstChild) {
      this.container.removeChild(this.container.firstChild);
    }

    // Phase 1: render without logo so the QR appears instantly
    const opts = this._buildQROptions();
    const logoUrl = opts.image;
    delete opts.image;
    delete opts.imageOptions;

    this.qrCode = new QRCodeStyling(opts);
    this.qrCode.append(this.container);

    if (this.options.showBadge && this.options.badgeUrl) {
      this._drawBadgeAfterRender();
    }

    // Phase 2: pre-load logo, re-render with it on success
    if (logoUrl) {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => {
        const fullOpts = this._buildQROptions();
        this.qrCode = new QRCodeStyling(fullOpts);
        while (this.container.firstChild) {
          this.container.removeChild(this.container.firstChild);
        }
        this.qrCode.append(this.container);
        if (this.options.showBadge && this.options.badgeUrl) {
          this._drawBadgeAfterRender();
        }
      };
      img.src = logoUrl;
    }
  }

  _drawBadgeAfterRender() {
    const renderVersion = ++this._renderVersion;

    const drawBadge = () => {
      if (this._renderVersion !== renderVersion) return;
      const canvas = this.container.querySelector("canvas");
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => {
        if (this._renderVersion !== renderVersion) return;
        const badgeSize = Math.round(canvas.width * 0.05);
        const margin = Math.round(canvas.width * 0.02);
        const x = canvas.width - badgeSize - margin;
        const y = canvas.height - badgeSize - margin;
        ctx.drawImage(img, x, y, badgeSize, badgeSize);
      };
      img.src = this.options.badgeUrl;
    };

    this.qrCode.getRawData("png").then(drawBadge).catch(drawBadge);
  }

  update(newOptions) {
    Object.assign(this.options, newOptions);
    this.render();
  }

  download(filename) {
    const canvas = this.container.querySelector("canvas");
    if (!canvas) return;

    canvas.toBlob((blob) => {
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = (filename || "qr-code") + ".png";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, "image/png");
  }

  setLogoFromFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      this.options.logoUrl = e.target.result;
      this.render();
    };
    reader.readAsDataURL(file);
  }
}
