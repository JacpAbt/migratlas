import { createPhoneDesk } from "./phone-desk";

(window as unknown as { createPhoneDesk: typeof createPhoneDesk }).createPhoneDesk = createPhoneDesk;
