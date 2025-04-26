<script>
    const { lat, lon, heading = 0 } = $props();
    // Compose a LatLngLiteral object for the center prop
    let center = { lat: Number(lat), lng: Number(lon) };
    // Ensure zoom is a number, not a string
    let zoom = 10;
</script>

<div class="relative rounded-xl" style="height: 400px;">
  <gmp-map
    {center}
    {zoom}
    map-id="DEMO_MAP_ID"
    style="height: 400px"
  ></gmp-map>
  <!-- Flight icon overlay, centered and rotated by heading -->
  <div
    class="absolute"
    style="
      left: 50%;
      top: 50%;
      transform: translate(-50%, -50%) rotate({heading}deg);
      pointer-events: none;
      z-index: 10;
    "
  >
    <img src="/flight.svg" alt="Plane" width="40" height="40" />
  </div>
</div>