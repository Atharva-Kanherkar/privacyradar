import {
  Activity,
  Baby,
  BadgeDollarSign,
  BarChart3,
  BookUser,
  Bot,
  BrainCircuit,
  CircleEllipsis,
  CircleSlash,
  Clock,
  CreditCard,
  Fingerprint,
  FlaskConical,
  FolderDown,
  Globe,
  HeartPulse,
  HelpCircle,
  Home,
  Image,
  LocateFixed,
  type LucideIcon,
  Mail,
  MapPin,
  Megaphone,
  MessageSquare,
  Mic,
  Network,
  Phone,
  Scale,
  Shield,
  ShoppingCart,
  SlidersHorizontal,
  Smartphone,
  ToggleLeft,
  Trash2,
  User,
  Wrench,
} from "lucide-react";

const ICONS: Record<string, LucideIcon> = {
  email: Mail,
  name: User,
  phone: Phone,
  address: Home,
  location: MapPin,
  precise_location: LocateFixed,
  device_id: Smartphone,
  ip_address: Network,
  browsing: Globe,
  purchase: ShoppingCart,
  payment: CreditCard,
  photos: Image,
  voice: Mic,
  messages: MessageSquare,
  contacts: BookUser,
  account_activity: Activity,
  inferred_profile: BrainCircuit,
  biometrics: Fingerprint,
  health: HeartPulse,
  children: Baby,
  other: CircleEllipsis,
  none_disclosed: CircleSlash,
  // purposes
  product: Wrench,
  analytics: BarChart3,
  advertising: Megaphone,
  personalization: SlidersHorizontal,
  security: Shield,
  legal: Scale,
  ai_training: Bot,
  research: FlaskConical,
  unspecified: HelpCircle,
  // sharing
  sale: BadgeDollarSign,
  third_party: Globe,
  advertising_partner: Megaphone,
  // control
  deletion: Trash2,
  opt_out: ToggleLeft,
  access: FolderDown,
  // retention
  duration_disclosed: Clock,
};

export function DataTypeIcon({
  attribute,
  size = 16,
  className,
}: {
  attribute: string;
  size?: number;
  className?: string;
}) {
  const Icon = ICONS[attribute] ?? CircleEllipsis;
  return <Icon size={size} className={className} aria-hidden="true" />;
}
