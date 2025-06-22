// src/features/config/components/tabs/Theme/BackgroundTechPattern.js
import React from 'react';

const BackgroundTechPattern = () => {
  return (
    <svg
      viewBox="0 0 925 646"
      width="100%"
      height="100%"
      preserveAspectRatio="xMidYMid slice"
      style={{
        position: 'absolute',
        inset: 0,
        zIndex: -1,
        pointerEvents: 'none',
      }}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <pattern
          id="pattern0"
          patternContentUnits="objectBoundingBox"
          width="1"
          height="1"
        >
          <image
            href={`${process.env.PUBLIC_URL}/icons/theme/tema001.png`}
            preserveAspectRatio="xMidYMid slice"
            width="1"
            height="1"
          />
        </pattern>
      </defs>

      {/* Fondo con patrón */}
      <rect width="925" height="646" fill="url(#pattern0)" />

      {/* Capa gris suave para que no se vea tan fuerte el patrón */}
      <g style={{ mixBlendMode: 'multiply' }}>
        <rect width="925" height="646" fill="#e0e0e0" opacity="0.3" />
      </g>
    </svg>
  );
};

export default BackgroundTechPattern;
