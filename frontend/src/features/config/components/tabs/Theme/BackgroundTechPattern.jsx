// src/components/BackgroundTechPattern.js
import React from 'react';

const BackgroundTechPattern = () => {
  return (
    <svg
      viewBox="0 0 925 646"
      width="100%"
      height="100%"
      preserveAspectRatio="xMidYMid slice"
      xmlns="http://www.w3.org/2000/svg"
      style={{
        position: 'absolute',
        inset: 0,
        zIndex: -1,
        pointerEvents: 'none',
        fill: 'none',
      }}
    >
      <defs>
        <pattern id="patternImg" patternUnits="userSpaceOnUse" width="925" height="646">
          <image
            href="/icons/theme/tema001.png"
            width="925"
            height="646"
            preserveAspectRatio="xMidYMid meet"
          />
        </pattern>

        <linearGradient id="fadeGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.6" />
          <stop offset="100%" stopColor="#243A5E" stopOpacity="0.0" />
        </linearGradient>

        <clipPath id="clipRect">
          <rect width="925" height="646" />
        </clipPath>
      </defs>

      <g clipPath="url(#clipRect)">
        {/* 1. Fondo azul base */}
        <rect width="925" height="646" fill="#243A5E" />

        {/* 2. Capas de patrón repetidas */}
        <rect
          width="1044.72"
          height="729.98"
          x="-59.72"
          y="-41"
          fill="url(#patternImg)"
          opacity="0.3"
          style={{ mixBlendMode: 'screen' }}
        />
        <rect
          width="1044.72"
          height="729.98"
          x="-59.72"
          y="-41"
          fill="url(#patternImg)"
          opacity="0.3"
          style={{ mixBlendMode: 'screen' }}
        />

        {/* 3. Degradado superior */}
        <rect
          width="1152.33"
          height="736.476"
          x="-113.165"
          y="-91.7776"
          fill="url(#fadeGradient)"
          style={{ mixBlendMode: 'screen' }}
        />
      </g>
    </svg>
  );
};

export default BackgroundTechPattern;
