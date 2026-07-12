import logoUrl from '../assets/prive-logo.png'

// Official Privé wordmark (colour variant, for light surfaces). Sized to sit
// within the header height; a white variant exists at ../assets/prive-logo-white.png.
export default function Logo() {
  return <img src={logoUrl} alt="Privé Technologies" className="h-8 w-auto object-contain block shrink-0" />
}
