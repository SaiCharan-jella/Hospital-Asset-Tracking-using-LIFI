/**
 * LiFi Optical Handoff Visualization
 * Creates animated visual representations of optical data transfers
 */

document.addEventListener('DOMContentLoaded', function () {
    initializeLiFiVisualization();
    animateOpticalZones();
    createDataFlowPaths();
});

/**
 * Initialize LiFi visualization elements
 */
function initializeLiFiVisualization() {
    const opticalZones = document.querySelectorAll('.optical-zone');

    opticalZones.forEach((zone, index) => {
        // Add random delay to animations for staggered effect
        zone.style.animationDelay = `${index * 0.1}s`;

        // Add connection lines between zones
        if (index < opticalZones.length - 1) {
            createConnectionLine(zone, opticalZones[index + 1]);
        }
    });
}

/**
 * Animate optical zones with light effects
 */
function animateOpticalZones() {
    const zones = document.querySelectorAll('.optical-zone');

    zones.forEach(zone => {
        const lightBeam = zone.querySelector('.light-beam');

        if (lightBeam) {
            // Random pulse intervals for realistic effect
            setInterval(() => {
                lightBeam.style.animation = 'none';
                setTimeout(() => {
                    lightBeam.style.animation = 'beam-pulse 2s ease-in-out infinite';
                }, 10);
            }, Math.random() * 5000 + 3000);
        }

        // Add hover effect
        zone.addEventListener('mouseenter', function () {
            this.style.boxShadow = `0 10px 30px ${this.style.borderColor}60`;
        });

        zone.addEventListener('mouseleave', function () {
            this.style.boxShadow = '';
        });
    });
}

/**
 * Create visual connection lines between optical zones
 */
function createConnectionLine(zone1, zone2) {
    // This would create SVG lines in a more complex implementation
    // For now, we'll add visual indicators
    const zoneContent = zone1.querySelector('.zone-content');
    if (zoneContent) {
        const indicator = document.createElement('div');
        indicator.className = 'transfer-indicator';
        indicator.style.cssText = `
            position: absolute;
            right: -10px;
            top: 50%;
            transform: translateY(-50%);
            width: 20px;
            height: 2px;
            background: linear-gradient(90deg, var(--lifi-blue), transparent);
            animation: flow 2s linear infinite;
        `;
        zoneContent.style.position = 'relative';
        zoneContent.appendChild(indicator);
    }
}

/**
 * Create animated data flow paths
 */
function createDataFlowPaths() {
    const maps = document.querySelectorAll('.optical-map');

    maps.forEach(map => {
        // Add canvas for drawing paths (optional enhancement)
        const canvas = document.createElement('canvas');
        canvas.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            opacity: 0.3;
        `;

        // Position the map relatively for canvas overlay
        if (map.style.position !== 'relative') {
            map.style.position = 'relative';
        }
    });
}

/**
 * Simulate active handoff session
 */
function simulateHandoffSession(fromZone, toZone) {
    const zones = document.querySelectorAll('.optical-zone');
    let fromElement, toElement;

    zones.forEach(zone => {
        const zoneName = zone.querySelector('.zone-name');
        if (zoneName) {
            if (zoneName.textContent === fromZone) fromElement = zone;
            if (zoneName.textContent === toZone) toElement = zone;
        }
    });

    if (fromElement && toElement) {
        // Highlight from zone
        fromElement.style.boxShadow = '0 0 20px var(--lifi-blue)';

        // Animate transfer
        setTimeout(() => {
            // Highlight to zone
            toElement.style.boxShadow = '0 0 20px var(--lifi-teal)';

            // Reset after animation
            setTimeout(() => {
                fromElement.style.boxShadow = '';
                toElement.style.boxShadow = '';
            }, 1000);
        }, 1000);
    }
}

/**
 * Update handoff status in real-time
 */
function updateHandoffStatus() {
    fetch('/api/active-sessions')
        .then(response => response.json())
        .then(sessions => {
            sessions.forEach(session => {
                // Visual representation of active sessions
                if (session.status === 'stable' && Math.random() > 0.7) {
                    // Randomly visualize some handoffs
                    const zones = ['Zone-A', 'Zone-B', 'Zone-C', 'Zone-D'];
                    const from = zones[Math.floor(Math.random() * zones.length)];
                    const to = zones[Math.floor(Math.random() * zones.length)];
                    if (from !== to) {
                        simulateHandoffSession(from, to);
                    }
                }
            });
        })
        .catch(error => console.log('Handoff visualization disabled'));
}

// Update visualization every 10 seconds
if (document.querySelector('.optical-map')) {
    setInterval(updateHandoffStatus, 10000);
}

// Add particle effect for data transfer
function createParticles() {
    const opticalMaps = document.querySelectorAll('.optical-map');

    opticalMaps.forEach(map => {
        setInterval(() => {
            const particle = document.createElement('div');
            particle.style.cssText = `
                position: absolute;
                width: 4px;
                height: 4px;
                background: var(--lifi-cyan);
                border-radius: 50%;
                pointer-events: none;
                animation: particle-float 3s ease-out forwards;
                left: ${Math.random() * 100}%;
                top: ${Math.random() * 100}%;
                box-shadow: 0 0 10px var(--lifi-cyan);
            `;

            if (map.style.position !== 'relative') {
                map.style.position = 'relative';
            }

            map.appendChild(particle);

            setTimeout(() => particle.remove(), 3000);
        }, 2000);
    });
}

// Add particle animation styles
const particleStyle = document.createElement('style');
particleStyle.textContent = `
    @keyframes particle-float {
        0% {
            transform: translateY(0) scale(1);
            opacity: 0.8;
        }
        100% {
            transform: translateY(-50px) scale(0);
            opacity: 0;
        }
    }
    
    @keyframes flow {
        0% {
            opacity: 0;
            transform: translateY(-50%) scaleX(0);
        }
        50% {
            opacity: 1;
        }
        100% {
            opacity: 0;
            transform: translateY(-50%) scaleX(1);
        }
    }
`;
document.head.appendChild(particleStyle);

// Initialize particles
if (document.querySelector('.optical-map')) {
    createParticles();
}
