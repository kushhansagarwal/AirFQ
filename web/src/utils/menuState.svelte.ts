export const menuState = () => {
  const menu = $state({
    isOpen: false,
    selectedTab: 'Flights', // Default selected tab
  });
  return menu;
};
